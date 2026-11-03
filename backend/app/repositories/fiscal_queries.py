"""Filtros compartilhados pela central, histórico e exportação fiscal."""
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, or_
from app.models.entities import Invoice, Student

LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")


def invoice_query(academy_id, q="", status="", start=None, end=None, origin="", student_id=None):
    if start and end and start > end:
        raise HTTPException(422, "Período inválido: a data inicial precisa ser anterior à final.")
    query = select(Invoice).where(Invoice.academy_id == academy_id)
    if q:
        term = f"%{q}%"
        query = query.join(Student, Student.id == Invoice.student_id).where(
            or_(Student.name.ilike(term), Invoice.identifier.ilike(term), Invoice.service_description.ilike(term)))
    if status == "pendentes":
        query = query.where(Invoice.status.in_(["rascunho", "aguardando_emissao", "processando"]))
    elif status:
        query = query.where(Invoice.status == status)
    # O banco guarda UTC sem tzinfo; o usuário escolhe dias no horário de Brasília.
    if start:
        instant = datetime.combine(start, time.min, LOCAL_ZONE).astimezone(timezone.utc).replace(tzinfo=None)
        query = query.where(Invoice.created_at >= instant)
    if end:
        instant = datetime.combine(end, time.max, LOCAL_ZONE).astimezone(timezone.utc).replace(tzinfo=None)
        query = query.where(Invoice.created_at <= instant)
    if origin:
        query = query.where(Invoice.origin == origin)
    if student_id:
        query = query.where(Invoice.student_id == student_id)
    return query
