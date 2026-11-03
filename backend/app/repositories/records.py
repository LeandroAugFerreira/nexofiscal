from datetime import date, datetime
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from app.models.entities import Student, Plan, Service, Contract, Charge, Payment, Invoice, Audit


def scoped(db, model, identity, academy_id, lock=False):
    query = select(model).where(model.id == identity, model.academy_id == academy_id)
    if lock:
        query = query.with_for_update()
    result = db.scalar(query)
    if not result:
        raise HTTPException(404, "Registro não encontrado.")
    return result


def audit(db, user, action, entity, identity=None, details=""):
    db.add(Audit(academy_id=user.academy_id, user_id=user.id, action=action,
        entity=entity, entity_id=identity, details=details))


def effective_status(row):
    if isinstance(row, Charge) and row.status == "pendente" and row.due_date < date.today():
        return "vencida"
    return row.status


def serialize(row, db=None, private=False):
    excluded = {"password_hash", "token_hash", "csrf_token", "document", "document_pdf", "document_xml", "document_snapshot", "request_hash"}
    result = {}
    for column in row.__table__.columns:
        if column.name in excluded:
            continue
        value = getattr(row, column.name)
        if isinstance(value, Decimal):
            value = format(value, ".2f")
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        if column.name == "cpf" and value and not private:
            value = "***.***.***-" + value[-2:]
        if isinstance(row,Student) and column.name=="cnpj" and value and not private:
            value="**.***.***/****-"+value[-2:]
        result[column.name] = value
    result["code"] = f"{row.id:06d}"
    if isinstance(row, Charge):
        result["balance"] = format(row.amount - row.paid, ".2f")
        result["status"] = effective_status(row)
    if db:
        if hasattr(row, "student_id"):
            result["student_name"] = db.get(Student, row.student_id).name
            result["client_name"] = result["student_name"]
            result["client_id"] = row.student_id
        if hasattr(row, "plan_id"):
            result["plan_name"] = db.get(Plan, row.plan_id).name
        if isinstance(row, Payment):
            charge = db.get(Charge, row.charge_id)
            result["student_name"] = db.get(Student, charge.student_id).name
        if isinstance(row, Charge):
            result["plan_name"] = db.get(Plan, db.get(Contract, row.contract_id).plan_id).name
        if isinstance(row, Invoice):
            result["has_pdf"]=bool(row.document_pdf)
            result["has_xml"]=bool(row.document_xml)
            if row.service_id:
                result["service_name"] = db.get(Service, row.service_id).name
            if row.charge_id and not row.competence:
                result["competence"] = db.get(Charge, row.charge_id).competence
    return result
