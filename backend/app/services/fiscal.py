import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select
from app.models.entities import Invoice, FiscalEvent, Charge, Student, Service, Contract, Plan, FiscalConfig
from app.repositories.records import scoped, audit
from app.fiscal.adapters.simulator import SimuladorFiscalAdapter
from app.utils.validation import valid_cpf, valid_cnpj

adapter = SimuladorFiscalAdapter()


def demo_config(db, academy_id):
    config = db.scalar(select(FiscalConfig).where(FiscalConfig.academy_id == academy_id))
    if not config or config.environment != "demonstracao" or config.provider != "simulador":
        raise HTTPException(422, "Somente o simulador em Demonstração está habilitado.")
    return config


def validate_direct(db, data, user):
    demo_config(db, user.academy_id)
    student = scoped(db, Student, data.student_id, user.academy_id)
    service = scoped(db, Service, data.service_id, user.academy_id)
    if student.status != "ativo" or service.status != "ativo":
        raise HTTPException(422, "Cliente e serviço precisam estar ativos para a emissão.")
    if not (valid_cnpj(student.cnpj or "") if student.person_type == "pj" else valid_cpf(student.cpf or "")):
        raise HTTPException(422, "Corrija o CPF ou CNPJ do cliente antes de emitir.")
    return student, service


def direct_fingerprint(data):
    payload=data.model_dump(mode="json")
    payload["amount"]=format(data.amount,".2f")
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def issue_direct(db, data, user, key):
    fingerprint = direct_fingerprint(data)
    existing = db.scalar(select(Invoice).where(Invoice.idempotency_key == key))
    if existing:
        if existing.academy_id != user.academy_id or existing.origin != "avulsa" or existing.request_hash != fingerprint:
            raise HTTPException(409, "Chave de operação já usada com outros dados fiscais.")
        return existing
    student, service = validate_direct(db, data, user)
    description = data.description or service.name
    invoice=Invoice(academy_id=user.academy_id,student_id=student.id,service_id=service.id,
        origin="avulsa",competence=data.competence,amount=data.amount,
        service_description=f"{description} • Competência {data.competence}",idempotency_key=key,request_hash=fingerprint)
    db.add(invoice)
    db.flush()
    event(db,invoice,"aguardando_emissao","Emissão avulsa simulada registrada; sem geração de pagamento ou cobrança")
    process(db,invoice,data.simulate_rejection)
    audit(db,user,"emitir_avulsa_simulada","notas_fiscais",invoice.id)
    return invoice


def eligibility(db, charge):
    student = db.get(Student, charge.student_id)
    reasons = []
    if charge.status == "cancelada":
        reasons.append("Cobrança cancelada")
    if charge.paid != charge.amount or charge.amount <= 0:
        reasons.append("Cobrança precisa estar integralmente paga")
    if student.status != "ativo":
        reasons.append("Cliente inativo")
    if not (valid_cnpj(student.cnpj or "") if student.person_type == "pj" else valid_cpf(student.cpf or "")):
        reasons.append("CPF ou CNPJ do cliente inválido")
    existing = db.scalar(select(Invoice).where(Invoice.charge_id == charge.id))
    if existing:
        reasons.append("Já existe solicitação fiscal para esta cobrança")
    return {"eligible": not reasons, "reasons": reasons}


def event(db, invoice, status, message):
    invoice.status = status
    db.add(FiscalEvent(invoice_id=invoice.id, status=status, message=message))


def issue(db, data, user, key):
    existing = db.scalar(select(Invoice).where(Invoice.idempotency_key == key))
    if existing:
        if existing.academy_id != user.academy_id or existing.origin != "cobranca" or existing.charge_id != data.charge_id:
            raise HTTPException(409, "Chave de operação já usada para outra cobrança.")
        return existing
    charge = scoped(db, Charge, data.charge_id, user.academy_id, lock=True)
    existing = db.scalar(select(Invoice).where(Invoice.charge_id == charge.id))
    if existing:
        return existing
    demo_config(db, user.academy_id)
    validation = eligibility(db, charge)
    if not validation["eligible"]:
        raise HTTPException(422, "; ".join(validation["reasons"]))
    contract = db.get(Contract, charge.contract_id)
    plan = db.get(Plan, contract.plan_id)
    invoice = Invoice(academy_id=user.academy_id, charge_id=charge.id, student_id=charge.student_id,
        amount=charge.amount, competence=charge.competence, service_description=f"{plan.name} • Competência {charge.competence}", idempotency_key=key)
    db.add(invoice)
    db.flush()
    event(db, invoice, "aguardando_emissao", "Solicitação simulada registrada")
    process(db, invoice, data.simulate_rejection)
    audit(db, user, "emitir_simulada", "notas_fiscais", invoice.id)
    return invoice


def process(db, invoice, reject=False):
    event(db, invoice, "processando", "Processamento pelo simulador local")
    invoice.attempts += 1
    adapter.emitir_nota(invoice, db.get(Student, invoice.student_id), reject, db=db)
    event(db, invoice, invoice.status, invoice.error or "Documento simulado gerado, sem validade fiscal")


def retry(db, invoice, user):
    adapter.consultar_nota(invoice)
    if invoice.status != "rejeitada":
        raise HTTPException(409, "Apenas rejeições simuladas podem ser reprocessadas.")
    demo_config(db, user.academy_id)
    if invoice.charge_id:
        charge = scoped(db, Charge, invoice.charge_id, user.academy_id, lock=True)
        if charge.paid != charge.amount or charge.status == "cancelada":
            raise HTTPException(422, "Cobrança não elegível.")
    elif scoped(db, Service, invoice.service_id, user.academy_id).status != "ativo":
        raise HTTPException(422, "Serviço inativo.")
    if db.get(Student, invoice.student_id).status != "ativo":
        raise HTTPException(422, "Cliente inativo.")
    process(db, invoice)
    audit(db, user, "reprocessar_simulada", "notas_fiscais", invoice.id)
    return invoice
