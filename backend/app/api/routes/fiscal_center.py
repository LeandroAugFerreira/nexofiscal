from decimal import Decimal
from datetime import date, datetime
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select, func, exists
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import Invoice, FiscalEvent, Charge, Student, Service, Academy, FiscalConfig
from app.schemas.inputs import DirectInvoiceInput
from app.security.auth import require
from app.services.fiscal import validate_direct, issue_direct, adapter, demo_config
from app.repositories.records import serialize
from app.repositories.fiscal_queries import invoice_query, LOCAL_ZONE
from app.api.routes.business import operation_key, PAGE_SIZE

router=APIRouter(prefix="/fiscal",tags=["Central de emissão"])


def ready_query(academy_id):
    return select(Charge).join(Student,Student.id==Charge.student_id).where(
        Charge.academy_id==academy_id,Student.status=="ativo",Charge.paid==Charge.amount,
        Charge.amount>0,Charge.status!="cancelada",
        ~exists().where(Invoice.charge_id==Charge.id))


@router.get("/overview")
def overview(q:str="", start:date|None=None, end:date|None=None, origin:str="",
    user=Depends(require("read")),db:Session=Depends(get_db)):
    filtered = invoice_query(user.academy_id, q=q, start=start, end=end, origin=origin)
    rows=db.scalars(filtered).all()
    counts={}
    for row in rows:
        counts[row.status]=counts.get(row.status,0)+1
    ready_count=db.scalar(select(func.count()).select_from(ready_query(user.academy_id).subquery()))
    config=db.scalar(select(FiscalConfig).where(FiscalConfig.academy_id==user.academy_id))
    configured=bool(config and config.environment=="demonstracao" and config.provider=="simulador")
    events=db.scalars(select(FiscalEvent).where(FiscalEvent.invoice_id.in_(filtered.with_only_columns(Invoice.id)))
        .order_by(FiscalEvent.id.desc()).limit(6)).all()
    timeline=[]
    for e in events:
        invoice=db.get(Invoice,e.invoice_id)
        timeline.append({**serialize(e),"identifier":invoice.identifier or f"Solicitação #{invoice.id:06d}",
            "client_name":db.get(Student,invoice.student_id).name})
    attention=[serialize(x,db) for x in sorted(rows,key=lambda x:x.id,reverse=True) if x.status in ("rejeitada","aguardando_emissao","processando")]
    academy=db.get(Academy,user.academy_id)
    return {"total":len(rows),"authorized":counts.get("autorizada",0),
        "pending":sum(counts.get(x,0) for x in ("rascunho","aguardando_emissao","processando")),
        "rejected":counts.get("rejeitada",0),"cancelled":counts.get("cancelada",0),"ready_charges":ready_count,
        "authorized_amount":format(sum((x.amount for x in rows if x.status=="autorizada"),Decimal("0")),".2f"),
        "connection":adapter.verificar_conexao() if configured else {"connected":False,"message":"Configuração fiscal incompatível com o simulador"},
        "environment":"demonstracao" if configured else "bloqueado","company_name":academy.name,
        "events":timeline,"attention":attention,
        "rejection_rate":format(Decimal(counts.get("rejeitada",0)*100)/len(rows),".1f") if rows else "0.0",
        "period":{"start":start.isoformat() if start else None,"end":end.isoformat() if end else None,
            "timezone":"America/Sao_Paulo"}}


@router.get("/scenarios")
def scenarios(user=Depends(require("fiscal")), db:Session=Depends(get_db)):
    demo_config(db, user.academy_id)
    # Apenas cadastros explicitamente fictícios. Abrir um exemplo não grava nem emite nota.
    clients=db.scalars(select(Student).where(Student.academy_id==user.academy_id,
        Student.status=="ativo", Student.notes.ilike("%fictício%")).order_by(Student.id)).all()
    service=db.scalar(select(Service).where(Service.academy_id==user.academy_id,
        Service.status=="ativo", Service.price>0, Service.description.ilike("%fictício%"))
        .order_by(Service.id).limit(1))
    examples=[]
    for key,person,title,reject in (("pf","pf","Cliente PF",False),("pj","pj","Cliente PJ",False),
        ("rejeicao","pf","Rejeição simulada",True)):
        client=next((x for x in clients if x.person_type==person),None)
        available=bool(client and service)
        examples.append({"id":key,"title":title,"available":available,
            "reason":"Cadastre cliente e serviço fictícios ativos para este exemplo." if not available else "",
            "form":{"client_id":client.id,"service_id":service.id,"amount":format(service.price,".2f"),
                "competence":datetime.now(LOCAL_ZONE).strftime("%Y-%m"),
                "description":f"{service.name} — exemplo de portfólio", "simulate_rejection":reject} if available else None})
    return {"environment":"demonstracao","items":examples}


@router.get("/ready-charges")
def ready_charges(q:str="",page:int=Query(1,ge=1),page_size:int=Query(PAGE_SIZE,ge=1,le=100),
    user=Depends(require("read")),db:Session=Depends(get_db)):
    query=ready_query(user.academy_id)
    if q:
        query=query.where(Student.name.ilike(f"%{q}%"))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.scalars(query.order_by(Charge.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items":[serialize(x,db) for x in rows],"total":total,"page":page,"page_size":page_size}


@router.post("/preview")
def preview(data:DirectInvoiceInput,user=Depends(require("fiscal")),db:Session=Depends(get_db)):
    student,service=validate_direct(db,data,user)
    academy=db.get(Academy,user.academy_id)
    return {"client":serialize(student),"service":serialize(service),"company":serialize(academy),
        "amount":format(data.amount,".2f"),"competence":data.competence,
        "description":data.description or service.name,"environment":"demonstracao","provider":"simulador",
        "checks":[{"id":key,"label":text,"passed":True} for key,text in (
            ("client","Cliente ativo e pertencente à empresa"),("service","Serviço ativo e pertencente à empresa"),
            ("amount","Valor positivo, com até duas casas decimais"),("competence","Competência no formato válido"),
            ("environment","Ambiente de demonstração / simulador local"))],
        "message":"DOCUMENTO SIMULADO — SEM VALIDADE FISCAL"}


@router.post("/issue-direct",status_code=201)
def emit_direct(data:DirectInvoiceInput,idempotency_key:str=Header(default=""),
    user=Depends(require("fiscal")),db:Session=Depends(get_db)):
    invoice=issue_direct(db,data,user,operation_key(idempotency_key))
    db.commit()
    return serialize(invoice,db)
