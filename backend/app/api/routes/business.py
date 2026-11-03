import csv
import io
import secrets
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import (Student, Plan, Service, Contract, Charge, Payment, Invoice, FiscalEvent,
    Academy, FiscalConfig, User, Audit, Automation, AutomationRun, utcnow)
from app.schemas.inputs import (StudentInput, PlanInput, ServiceInput, ContractInput, ContractStatus,
    ChargeInput, PaymentInput, InvoiceInput, CancelInput, AcademyInput, FiscalConfigInput, AutomationToggle)
from app.security.auth import require, PERMISSIONS
from app.repositories.records import scoped, serialize, audit, effective_status
from app.repositories.fiscal_queries import invoice_query
from app.services.finance import create_contract, create_charge, register_payment
from app.services.fiscal import issue, retry, event, adapter, eligibility
from app.automations.integration import connection, dispatch
from app.automations.routines import describe, CATALOG as ROUTINES
from app.core.config import settings

router = APIRouter(tags=["FitNota"])
CATALOG = {"students": (Student, StudentInput, "students"), "clients": (Student, StudentInput, "students"), "plans": (Plan, PlanInput, "catalog"),
    "services": (Service, ServiceInput, "catalog")}


PAGE_SIZE = 5


def paginated(db, model, academy_id, q="", status="", page=1, page_size=PAGE_SIZE, student_id=None, start=None, end=None, origin=""):
    query = select(model).where(model.academy_id == academy_id)
    if model is Invoice:
        query = invoice_query(academy_id, q, status, start, end, origin, student_id)
    elif q and hasattr(model, "name"):
        query = query.where(model.name.ilike(f"%{q}%"))
    elif q:
        if model is Payment:
            query = query.join(Charge, Charge.id == Payment.charge_id).join(Student, Student.id == Charge.student_id)
        elif hasattr(model, "student_id"):
            query = query.join(Student, Student.id == model.student_id)
        else:
            query = query.where(model.id == int(q) if q.isdigit() else False)
        if model is Payment or hasattr(model, "student_id"):
            query = query.where(Student.name.ilike(f"%{q}%"))
    if model is not Invoice and status and hasattr(model, "status"):
        if model is Charge and status == "vencida":
            query = query.where(Charge.status == "pendente", Charge.due_date < date.today())
        elif model is Charge and status == "pendente":
            query = query.where(Charge.status == "pendente", Charge.due_date >= date.today())
        else:
            query = query.where(model.status == status)
    if model is not Invoice and student_id and hasattr(model, "student_id"):
        query = query.where(model.student_id == student_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(model.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [serialize(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


def register_catalog(resource, model, schema, permission):
    def list_records(q: str = "", status: str = "", page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100),
        user=Depends(require("read")), db: Session = Depends(get_db)):
        return paginated(db, model, user.academy_id, q, status, page, page_size)

    def get_record(identity: int, user=Depends(require("read")), db: Session = Depends(get_db)):
        return serialize(scoped(db, model, identity, user.academy_id), db,
            private=model is Student and "students" in PERMISSIONS[user.role])

    def create_record(data, user=Depends(require(permission)), db: Session = Depends(get_db)):
        record = model(academy_id=user.academy_id, **data.model_dump())
        db.add(record)
        db.flush()
        audit(db, user, "criar", model.__tablename__, record.id)
        db.commit()
        return serialize(record, db)

    def edit_record(identity: int, data, user=Depends(require(permission)), db: Session = Depends(get_db)):
        record = scoped(db, model, identity, user.academy_id)
        for key, value in data.model_dump().items():
            setattr(record, key, value)
        audit(db, user, "editar", model.__tablename__, identity)
        db.commit()
        return serialize(record, db)

    def deactivate(identity: int, user=Depends(require(permission)), db: Session = Depends(get_db)):
        record = scoped(db, model, identity, user.academy_id)
        record.status = "inativo"
        audit(db, user, "inativar", model.__tablename__, identity)
        db.commit()
        return serialize(record, db)

    create_record.__annotations__["data"] = schema
    edit_record.__annotations__["data"] = schema
    router.add_api_route(f"/{resource}", list_records, methods=["GET"], name=f"list_{resource}")
    router.add_api_route(f"/{resource}/{{identity}}", get_record, methods=["GET"], name=f"get_{resource}")
    router.add_api_route(f"/{resource}", create_record, methods=["POST"], name=f"create_{resource}", status_code=201)
    router.add_api_route(f"/{resource}/{{identity}}", edit_record, methods=["PUT"], name=f"edit_{resource}")
    router.add_api_route(f"/{resource}/{{identity}}", deactivate, methods=["DELETE"], name=f"deactivate_{resource}")


for resource, (model, schema, permission) in CATALOG.items():
    register_catalog(resource, model, schema, permission)


@router.get("/clients/{identity}/history")
@router.get("/students/{identity}/history")
def student_history(identity: int, user=Depends(require("read")), db: Session = Depends(get_db)):
    scoped(db, Student, identity, user.academy_id)
    charges = db.scalars(select(Charge).where(Charge.student_id == identity)).all()
    ids = [c.id for c in charges]
    contracts = db.scalars(select(Contract).where(Contract.student_id == identity)).all()
    payments = db.scalars(select(Payment).where(Payment.charge_id.in_(ids))).all()
    invoices = db.scalars(select(Invoice).where(Invoice.student_id == identity)).all()
    return {"contracts": [serialize(x, db) for x in contracts], "charges": [serialize(x, db) for x in charges],
        "payments": [serialize(x, db) for x in payments], "invoices": [serialize(x, db) for x in invoices]}


MODELS = {"contracts": Contract, "charges": Charge, "payments": Payment, "invoices": Invoice}


def register_financial_list(resource, model):
    def listing(q: str = "", status: str = "", student_id: int | None = None, start:date|None=None,end:date|None=None,origin:str="",
        page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100),
        user=Depends(require("read")), db: Session = Depends(get_db)):
        return paginated(db, model, user.academy_id, q, status, page, page_size, student_id, start, end, origin)
    router.add_api_route(f"/{resource}", listing, methods=["GET"], name=f"list_{resource}")


for resource, model in MODELS.items():
    register_financial_list(resource, model)


@router.post("/contracts", status_code=201)
def contract_create(data: ContractInput, user=Depends(require("finance")), db: Session = Depends(get_db)):
    row = create_contract(db, data, user)
    db.commit()
    return serialize(row, db)


@router.patch("/contracts/{identity}")
def contract_update(identity: int, data: ContractStatus, user=Depends(require("finance")), db: Session = Depends(get_db)):
    row = scoped(db, Contract, identity, user.academy_id)
    if row.status == "cancelado":
        raise HTTPException(409, "Contrato cancelado não pode ser reativado.")
    row.status = data.status
    audit(db, user, "alterar_status", "contratos", identity, data.status)
    db.commit()
    return serialize(row, db)


@router.post("/charges", status_code=201)
def charge_create(data: ChargeInput, user=Depends(require("finance")), db: Session = Depends(get_db)):
    row = create_charge(db, data, user)
    db.commit()
    return serialize(row, db)


def operation_key(key):
    if not key or len(key) < 8 or len(key) > 100:
        raise HTTPException(422, "Informe Idempotency-Key de 8 a 100 caracteres.")
    return key


@router.post("/payments", status_code=201)
def payment_create(data: PaymentInput, idempotency_key: str = Header(default=""),
    user=Depends(require("finance")), db: Session = Depends(get_db)):
    row = register_payment(db, data, user, operation_key(idempotency_key))
    db.commit()
    return serialize(row, db)


@router.get("/charges/{identity}/eligibility")
def charge_eligibility(identity: int, user=Depends(require("read")), db: Session = Depends(get_db)):
    return eligibility(db, scoped(db, Charge, identity, user.academy_id))


@router.post("/invoices", status_code=201)
def invoice_create(data: InvoiceInput, idempotency_key: str = Header(default=""),
    user=Depends(require("fiscal")), db: Session = Depends(get_db)):
    row = issue(db, data, user, operation_key(idempotency_key))
    db.commit()
    return serialize(row, db)


@router.get("/invoices/{identity}")
def invoice_detail(identity: int, user=Depends(require("read")), db: Session = Depends(get_db)):
    row = scoped(db, Invoice, identity, user.academy_id)
    result = serialize(row, db)
    result["events"] = [serialize(x) for x in db.scalars(select(FiscalEvent).where(FiscalEvent.invoice_id == identity).order_by(FiscalEvent.id)).all()]
    result["consultation"] = adapter.consultar_nota(row)
    return result


@router.get("/invoices/{identity}/document", response_class=HTMLResponse)
def invoice_document(identity: int, user=Depends(require("read")), db: Session = Depends(get_db)):
    row = scoped(db, Invoice, identity, user.academy_id)
    if not row.document:
        raise HTTPException(404, "Documento ainda não disponível.")
    audit(db, user, "obter_documento", "notas_fiscais", identity)
    db.commit()
    return HTMLResponse(adapter.obter_documento(row), headers={"Content-Disposition": f'inline; filename="{row.identifier}.html"',
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:"})


@router.post("/invoices/{identity}/cancel")
def invoice_cancel(identity: int, data: CancelInput, user=Depends(require("cancel")), db: Session = Depends(get_db)):
    row = scoped(db, Invoice, identity, user.academy_id, lock=True)
    if row.status != "autorizada":
        raise HTTPException(409, "Apenas documentos simulados autorizados podem ser cancelados.")
    event(db, row, "cancelamento_solicitado", data.reason)
    adapter.cancelar_nota(row, data.reason)
    event(db, row, "cancelada", "Cancelamento simulado concluído")
    audit(db, user, "cancelar_simulada", "notas_fiscais", identity)
    db.commit()
    return serialize(row, db)


@router.post("/invoices/{identity}/retry")
def invoice_retry(identity: int, user=Depends(require("fiscal")), db: Session = Depends(get_db)):
    row = retry(db, scoped(db, Invoice, identity, user.academy_id, lock=True), user)
    db.commit()
    return serialize(row, db)


@router.get("/company")
@router.get("/academy")
def academy_get(user=Depends(require("read")), db: Session = Depends(get_db)):
    return serialize(db.get(Academy, user.academy_id))


@router.put("/company")
@router.put("/academy")
def academy_edit(data: AcademyInput, user=Depends(require("settings")), db: Session = Depends(get_db)):
    row = db.get(Academy, user.academy_id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    audit(db, user, "editar", "academias", row.id)
    db.commit()
    return serialize(row)


@router.get("/fiscal-config")
def config_get(user=Depends(require("read")), db: Session = Depends(get_db)):
    row = db.scalar(select(FiscalConfig).where(FiscalConfig.academy_id == user.academy_id))
    services = db.scalars(select(Service).where(Service.academy_id == user.academy_id)).all()
    return {**serialize(row), "connection": adapter.verificar_conexao(), "real_transmission_enabled": False,
        "metrics": [{"title":"Ambiente atual","value":"Demonstração","kind":"text"},
            {"title":"Serviços cadastrados","value":str(len(services)),"kind":"number"},
            {"title":"Adaptadores funcionais","value":"1","kind":"number"},
            {"title":"Transmissões oficiais","value":"0","kind":"number"}]}


@router.put("/fiscal-config")
def config_edit(data: FiscalConfigInput, user=Depends(require("settings")), db: Session = Depends(get_db)):
    row = db.scalar(select(FiscalConfig).where(FiscalConfig.academy_id == user.academy_id))
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    audit(db, user, "editar", "configuracoes_fiscais", row.id)
    db.commit()
    return serialize(row)


@router.get("/users")
def users(user=Depends(require("users")), db: Session = Depends(get_db)):
    result=[]
    for row in db.scalars(select(User).where(User.academy_id == user.academy_id)).all():
        latest=db.scalar(select(Audit).where(Audit.user_id==row.id,Audit.action=="login").order_by(Audit.id.desc()).limit(1))
        result.append({**serialize(row),"last_login":latest.created_at.isoformat() if latest else None})
    return result


@router.get("/audit")
def audits(page: int = Query(1, ge=1), user=Depends(require("audit")), db: Session = Depends(get_db)):
    return paginated(db, Audit, user.academy_id, page=page, page_size=PAGE_SIZE)


@router.get("/automations")
def automations(page: int = Query(1, ge=1), status: str = Query('', pattern='^(|sucesso|erro|ignorada|encaminhada|pendente)$'),
    user=Depends(require("read")), db: Session = Depends(get_db)):
    workflows = db.scalars(select(Automation).where(Automation.academy_id == user.academy_id)).all()
    ids = [x.id for x in workflows]
    run_query = select(AutomationRun).where(AutomationRun.automation_id.in_(ids))
    if status:
        run_query = run_query.where(AutomationRun.status == status)
    runs_total = db.scalar(select(func.count()).select_from(run_query.subquery()))
    runs = db.scalars(run_query.order_by(AutomationRun.id.desc()).offset((page-1)*PAGE_SIZE).limit(PAGE_SIZE)).all()
    all_runs=db.scalars(select(AutomationRun).where(AutomationRun.automation_id.in_(ids))).all()
    todays=[x for x in all_runs if x.created_at.date()==utcnow().date()]
    connection_status=connection()
    workflow_names = {x.id: describe(x)['name'] for x in workflows}
    return {"connection": connection_status, "workflows": [{**serialize(x), **describe(x)} for x in workflows],
        "runs_total": runs_total, "runs_count": len(all_runs), "page": page, "page_size": PAGE_SIZE,
        "runs": [{**serialize(x), 'workflow_name': workflow_names[x.automation_id]} for x in runs],
        "metrics": [{"title":"Rotinas habilitadas","value":str(sum(x.enabled and x.workflow_key in ROUTINES for x in workflows)),"kind":"number"},
            {"title":"Execuções hoje (UTC)","value":str(len(todays)),"kind":"number"},
            {"title":"Falhas hoje (UTC)","value":str(sum(x.status=="erro" for x in todays)),"kind":"number","tone":"warning"},
            {"title":"Conexão com n8n","value":"Disponível" if connection_status['connected'] else "Indisponível","kind":"text"}]}


@router.patch("/automations/{identity}")
def automation_toggle(identity: int, data: AutomationToggle, user=Depends(require("automation")), db: Session = Depends(get_db)):
    row = scoped(db, Automation, identity, user.academy_id)
    if row.workflow_key not in ROUTINES:
        raise HTTPException(422, "Workflow reservado para uma versão futura.")
    row.enabled = data.enabled
    audit(db, user, "ativar" if data.enabled else "desativar", "automacoes", row.id)
    db.commit()
    return serialize(row)


@router.post("/automations/dispatch/{charge_id}")
def automation_dispatch(charge_id: int, user=Depends(require("automation")), db: Session = Depends(get_db)):
    charge = scoped(db, Charge, charge_id, user.academy_id)
    if charge.paid != charge.amount:
        raise HTTPException(422, "Selecione uma cobrança paga.")
    row = dispatch(db, charge, user.academy_id)
    audit(db, user, "encaminhar_evento", "automacoes", row.automation_id)
    db.commit()
    return serialize(row)


def automation_user(x_automation_token: str = Header(default=""), db: Session = Depends(get_db)):
    token = settings().automation_token
    if len(token) < 32 or not secrets.compare_digest(token, x_automation_token):
        raise HTTPException(401, "Integração não autenticada.")
    # v0.1 possui uma academia; a identidade técnica é o administrador do seed.
    user = db.scalar(select(User).where(User.email == settings().demo_email, User.active.is_(True), User.role == "administrador"))
    if not user:
        raise HTTPException(503, "Identidade técnica não configurada.")
    return user


@router.get("/automation/charges/{identity}")
def automation_charge(identity: int, user=Depends(automation_user), db: Session = Depends(get_db)):
    row = scoped(db, Charge, identity, user.academy_id)
    return {"id": row.id, "status": effective_status(row), **eligibility(db, row)}


@router.post("/automation/issue/{identity}")
def automation_issue(identity: int, user=Depends(automation_user), db: Session = Depends(get_db)):
    row = issue(db, InvoiceInput(charge_id=identity), user, f"automation-charge-{identity}")
    audit(db, user, "webhook_simulado", "notas_fiscais", row.id)
    db.commit()
    return {"id": row.id, "status": row.status, "identifier": row.identifier, "simulated": True}


@router.get("/dashboard")
def dashboard(user=Depends(require("read")), db: Session = Depends(get_db)):
    def rows(model):
        return db.scalars(select(model).where(model.academy_id == user.academy_id)).all()
    students, contracts, charges, payments, invoices = map(rows, (Student, Contract, Charge, Payment, Invoice))
    valid = [x for x in charges if x.status != "cancelada"]
    expected = sum((x.amount for x in valid), Decimal("0"))
    received = sum((x.amount for x in payments), Decimal("0"))
    balance = sum((x.amount - x.paid for x in valid), Decimal("0"))
    overdue = sum((x.amount-x.paid for x in valid if x.due_date < date.today()), Decimal("0"))
    monthly = {}
    monthly_expected = {}
    charge_states = {}
    for c in valid:
        monthly_expected[c.competence] = monthly_expected.get(c.competence, Decimal("0")) + c.amount
        state = effective_status(c)
        charge_states[state] = charge_states.get(state, 0) + 1
    for p in payments:
        key = p.paid_at.strftime("%Y-%m")
        monthly[key] = monthly.get(key, Decimal("0")) + p.amount
    methods, plans, states = {}, {}, {}
    for p in payments:
        methods[p.method] = methods.get(p.method, Decimal("0")) + p.amount
        c = db.get(Charge, p.charge_id)
        plan = db.get(Plan, db.get(Contract, c.contract_id).plan_id).name
        plans[plan] = plans.get(plan, Decimal("0")) + p.amount
    for n in invoices:
        states[n.status] = states.get(n.status, 0) + 1
    growth = {}
    for s in students:
        key = s.created_at.strftime("%Y-%m")
        growth[key] = growth.get(key, 0) + 1
    cumulative = 0
    evolution = []
    for month in sorted(growth):
        cumulative += growth[month]
        evolution.append({"name": month, "value": cumulative})
    def pairs(mapping):
        return [{"name": k, "value": str(v) if isinstance(v, Decimal) else v} for k, v in mapping.items()]
    return {"active_students": sum(x.status == "ativo" for x in students), "active_contracts": sum(x.status == "ativo" for x in contracts),
        "expected": str(expected), "received": str(received), "balance": str(balance), "overdue": str(overdue),
        "delinquency": str((overdue/expected*100).quantize(Decimal("0.1"))) if expected else "0",
        "authorized_invoices": states.get("autorizada", 0), "pending_invoices": sum(states.get(x, 0) for x in ("rascunho", "aguardando_emissao", "processando")),
        "rejected_invoices": states.get("rejeitada", 0), "monthly_revenue": [{"name": k, "value": str(monthly.get(k, Decimal('0'))), "expected": str(monthly_expected.get(k, Decimal('0')))} for k in sorted(set(monthly)|set(monthly_expected))],
        "charge_status": pairs(charge_states),
        "payment_methods": pairs(methods), "plan_revenue": pairs(plans), "invoice_status": pairs(states), "student_evolution": evolution,
        "latest_charges": [serialize(x, db) for x in sorted(charges, key=lambda x:x.id, reverse=True)[:5]],
        "latest_payments": [serialize(x, db) for x in sorted(payments, key=lambda x:(x.paid_at,x.id), reverse=True)[:5]],
        "latest_invoices": [serialize(x, db) for x in sorted(invoices, key=lambda x:x.id, reverse=True)[:5]],
        "fiscal_connection": adapter.verificar_conexao(), "n8n_connection": connection()}


@router.get("/reports/{resource}.csv")
def csv_report(resource: str, start: date | None = None, end: date | None = None, status: str = "",
    student_id: int | None = None, plan_id: int | None = None, q: str = "", origin: str = "",
    user=Depends(require("read")), db: Session = Depends(get_db)):
    model = MODELS.get(resource)
    if not model:
        raise HTTPException(404, "Relatório não disponível.")
    if start and end and start > end:
        raise HTTPException(422, "Período inválido.")
    query = select(model).where(model.academy_id == user.academy_id)
    if model is Invoice:
        query = invoice_query(user.academy_id, q, status, start, end, origin, student_id)
    rows = db.scalars(query.order_by(model.id)).all()
    records = []
    for row in rows:
        charge = db.get(Charge, row.charge_id) if isinstance(row, (Payment, Invoice)) and row.charge_id else row if isinstance(row, Charge) else None
        contract = db.get(Contract, charge.contract_id) if charge else row if isinstance(row,Contract) else None
        sid = charge.student_id if charge else row.student_id
        when = row.paid_at if isinstance(row, Payment) else row.due_date if isinstance(row, Charge) else row.start_date if isinstance(row, Contract) else row.created_at.date()
        if model is not Invoice and (start and when < start or end and when > end or status and effective_status(row) != status or student_id and sid != student_id):
            continue
        if plan_id and (not contract or contract.plan_id != plan_id):
            continue
        records.append(serialize(row, db))
    output = io.StringIO()
    columns = ["code", "student_name", "status", "amount", "created_at"]
    if model is Invoice:
        columns += ["identifier", "environment", "origin", "competence", "service_description"]
    if model is Charge:
        columns += ["competence", "due_date", "paid", "balance"]
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", delimiter=";")
    writer.writeheader()
    for record in records:
        # Neutraliza fórmulas ao abrir no Excel.
        writer.writerow({k: "'"+str(v) if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v for k,v in record.items()})
    audit(db, user, "exportar_csv", resource)
    db.commit()
    return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="nexofiscal-{resource}.csv"'})
