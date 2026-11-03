from decimal import Decimal
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select, update
from app.models.entities import Student, Plan, Contract, Charge, Payment
from app.repositories.records import scoped, audit


def create_contract(db, data, user):
    student = scoped(db, Student, data.student_id, user.academy_id)
    plan = scoped(db, Plan, data.plan_id, user.academy_id)
    if student.status != "ativo" or plan.status != "ativo":
        raise HTTPException(422, "Aluno e plano precisam estar ativos.")
    values = data.model_dump()
    values["amount"] = plan.price if data.amount is None else data.amount
    contract = Contract(academy_id=user.academy_id, **values)
    db.add(contract)
    db.flush()
    audit(db, user, "criar", "contratos", contract.id)
    return contract


def create_charge(db, data, user):
    contract = scoped(db, Contract, data.contract_id, user.academy_id)
    if contract.status != "ativo":
        raise HTTPException(422, "Contrato precisa estar ativo.")
    if data.due_date < contract.start_date or (contract.end_date and data.due_date > contract.end_date):
        raise HTTPException(422, "Vencimento deve estar dentro da vigência do contrato.")
    if db.scalar(select(Charge).where(Charge.contract_id == contract.id, Charge.competence == data.competence)):
        raise HTTPException(409, "Já existe cobrança para este contrato e competência.")
    amount = contract.amount - data.discount + data.surcharge
    if amount <= Decimal("0"):
        raise HTTPException(422, "Valor final precisa ser positivo.")
    charge = Charge(academy_id=user.academy_id, student_id=contract.student_id,
        original_amount=contract.amount, amount=amount, **data.model_dump())
    db.add(charge)
    db.flush()
    audit(db, user, "gerar", "cobrancas", charge.id)
    return charge


def register_payment(db, data, user, key):
    existing = db.scalar(select(Payment).where(Payment.idempotency_key == key))
    if existing:
        if existing.academy_id != user.academy_id or any(getattr(existing, field) != getattr(data, field) for field in ("charge_id", "amount", "paid_at", "method", "reference")):
            raise HTTPException(409, "Chave de operação já usada com outro pagamento.")
        return existing
    if data.paid_at > date.today():
        raise HTTPException(422, "Pagamento não pode ter data futura.")
    charge = scoped(db, Charge, data.charge_id, user.academy_id, lock=True)
    if charge.status == "cancelada":
        raise HTTPException(422, "Cobrança cancelada.")
    # Condição no UPDATE protege também SQLite, que não suporta SELECT FOR UPDATE.
    result = db.execute(update(Charge).where(Charge.id == charge.id,
        Charge.paid + data.amount <= Charge.amount, Charge.status != "cancelada")
        .values(paid=Charge.paid + data.amount).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise HTTPException(422, "Pagamento excede o saldo da cobrança.")
    db.refresh(charge)
    charge.status = "paga" if charge.paid == charge.amount else "parcialmente_paga"
    payment = Payment(academy_id=user.academy_id, idempotency_key=key, **data.model_dump())
    db.add(payment)
    db.flush()
    audit(db, user, "registrar_manual", "pagamentos", payment.id)
    return payment
