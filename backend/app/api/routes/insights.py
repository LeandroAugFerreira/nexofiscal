from datetime import date
from decimal import Decimal
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import Student, Plan, Service, Contract, Charge, Payment, Invoice, User, Audit
from app.security.auth import require, PERMISSIONS
from app.repositories.records import effective_status
from app.api.routes.business import paginated, PAGE_SIZE

router = APIRouter(tags=["Indicadores"])


@router.get("/search")
def search(q: str = "", paginate: bool = False, page: int = Query(1, ge=1),
    user=Depends(require("read")), db: Session = Depends(get_db)):
    if len(q.strip()) < 2:
        return {"items": [], "total": 0, "page": page, "page_size": PAGE_SIZE} if paginate else []
    results = []
    for resource, model in (("clients",Student),("plans",Plan),("services",Service),("charges",Charge),("invoices",Invoice)):
        listing = paginated(db, model, user.academy_id, q=q[:100], page_size=4)
        if paginate and listing['total'] > 4:
            listing = paginated(db, model, user.academy_id, q=q[:100], page_size=listing['total'])
        for item in listing["items"]:
            results.append({"resource":resource,"id":item["id"],"title":item.get("name") or item.get("student_name"),
                "description":item.get("identifier") or f"#{item['code']}"})
    if paginate:
        return {"items": results[(page-1)*PAGE_SIZE:page*PAGE_SIZE], "total": len(results), "page": page, "page_size": PAGE_SIZE}
    return results


@router.get("/insights/{resource}")
def insights(resource: str, user=Depends(require("read")), db: Session = Depends(get_db)):
    models={"students":Student,"clients":Student,"plans":Plan,"services":Service,"contracts":Contract,"charges":Charge,"payments":Payment,"invoices":Invoice,"users":User}
    model=models.get(resource)
    if not model:
        raise HTTPException(404,"Indicadores não disponíveis")
    if resource=="users" and "users" not in PERMISSIONS.get(user.role,set()):
        raise HTTPException(403,"Seu perfil não permite esta consulta")
    rows=db.scalars(select(model).where(model.academy_id==user.academy_id)).all()
    metrics=[]
    distribution=[]
    def metric(title,value,kind="number",tone="neutral"):
        metrics.append({"title":title,"value":str(value),"kind":kind,"tone":tone})
    if resource=="users":
        metric("Usuários ativos",sum(x.active for x in rows))
        metric("Administradores",sum(x.role=="administrador" for x in rows))
        metric("Perfis financeiros",sum(x.role=="financeiro" for x in rows))
        logins=db.scalars(select(Audit).where(Audit.academy_id==user.academy_id,Audit.action=="login")).all()
        metric("Acessos hoje (UTC)",sum(x.created_at.date()==date.today() for x in logins))
        distribution=[{"name":k,"value":v} for k,v in Counter(x.role for x in rows).items()]
    elif resource in ("students","clients"):
        charges=db.scalars(select(Charge).where(Charge.academy_id==user.academy_id,Charge.due_date<date.today(),Charge.paid<Charge.amount,Charge.status!="cancelada")).all()
        metric("Clientes ativos",sum(x.status=="ativo" for x in rows))
        metric("Clientes inativos",sum(x.status=="inativo" for x in rows))
        metric("Aniversariantes do mês",sum(bool(x.birth_date and x.birth_date.month==date.today().month) for x in rows))
        metric("Clientes com saldo vencido",len({x.student_id for x in charges}),tone="warning")
        counts=Counter()
        for c in db.scalars(select(Contract).where(Contract.academy_id==user.academy_id,Contract.status=="ativo")).all():
            counts[db.get(Plan,c.plan_id).name]+=1
        distribution=[{"name":name,"value":value} for name,value in counts.items()]
    elif resource in ("plans","services"):
        metric("Planos ativos" if resource=="plans" else "Serviços ativos",sum(x.status=="ativo" for x in rows))
        metric("Valor médio cadastrado",sum((x.price for x in rows),Decimal('0'))/len(rows) if rows else 0,"money")
        metric("Total de cadastros",len(rows))
        metric("Inativos",sum(x.status=="inativo" for x in rows))
        distribution=[{"name":x.name,"value":str(x.price)} for x in rows]
    elif resource=="contracts":
        for status,title in (("ativo","Contratos ativos"),("suspenso","Contratos suspensos"),("cancelado","Contratos cancelados")):
            metric(title,sum(x.status==status for x in rows))
        metric("Valor dos contratos ativos",sum((x.amount for x in rows if x.status=="ativo"),Decimal('0')),"money")
    elif resource=="charges":
        valid=[x for x in rows if x.status!="cancelada"]
        metric("Total previsto",sum((x.amount for x in valid),Decimal('0')),"money")
        metric("Total em aberto",sum((x.amount-x.paid for x in valid),Decimal('0')),"money", "warning")
        metric("Saldo vencido",sum((x.amount-x.paid for x in valid if x.due_date<date.today()),Decimal('0')),"money", "warning")
        metric("Total registrado como pago",sum((x.paid for x in valid),Decimal('0')),"money", "positive")
    elif resource=="payments":
        total=sum((x.amount for x in rows),Decimal('0'))
        metric("Total recebido manualmente",total,"money","positive")
        metric("Quantidade de pagamentos",len(rows))
        metric("Confirmações bancárias",0)
        metric("Ticket médio registrado",total/len(rows) if rows else 0,"money")
        amounts={}
        for x in rows:
            amounts[x.method]=amounts.get(x.method,Decimal('0'))+x.amount
        distribution=[{"name":k,"value":str(v)} for k,v in amounts.items()]
    elif resource=="invoices":
        for statuses,title in ((['autorizada'],'Autorizadas no simulador'),(['aguardando_emissao','processando'],'Pendentes'),(['rejeitada'],'Rejeitadas no simulador'),(['cancelada'],'Canceladas no simulador')):
            metric(title,sum(x.status in statuses for x in rows))
    if not distribution:
        distribution=[{"name":k,"value":v} for k,v in Counter(effective_status(x) for x in rows).items()]
    return {"metrics":metrics,"distribution":distribution,"basis":"Todos os registros da academia; sem comparativo temporal"}
