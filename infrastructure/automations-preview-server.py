"""QA de automações em banco separado. Não conecta SMTP/n8n externos."""
import os
import sys
from pathlib import Path
from uuid import uuid4
from datetime import date, timedelta
from decimal import Decimal

root = Path(__file__).resolve().parents[1]
temporary = root / '.tmp'; temporary.mkdir(exist_ok=True)
os.environ.update({'DATABASE_URL': 'sqlite:///' + (temporary / f'automations-qa-{uuid4().hex}.db').as_posix(),
    'PORTFOLIO_ENABLED': 'false', 'SMTP_HOST': '', 'SMTP_USERNAME': '', 'SMTP_PASSWORD': '', 'SMTP_FROM_EMAIL': '',
    'N8N_HEALTH_URL': '', 'N8N_WEBHOOK_URL': '', 'AUTOMATION_TOKEN': '', 'COOKIE_SECURE': 'false'})
sys.path.insert(0, str(root / 'backend'))
from app.database.session import Base, engine, SessionLocal
from app.models.entities import Academy, FiscalConfig, User, Student, Plan, Contract, Charge, Payment, Automation
from app.security.auth import hasher
from app.automations.routines import CATALOG
from app.main import app
import uvicorn

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        company = Academy(name='Empresa QA', legal_name='Empresa fictícia de QA', cnpj='00000000000191')
        db.add(company); db.flush()
        db.add(FiscalConfig(academy_id=company.id))
        db.add(User(academy_id=company.id, name='Administrador QA', email='admin@example.com', role='administrador', password_hash=hasher.hash('Automations-QA-admin-123')))
        client = Student(academy_id=company.id, name='Cliente Fictício QA', cpf='52998224725')
        plan = Plan(academy_id=company.id, name='Consultoria QA', price=Decimal('119.90'), period_months=1)
        db.add_all([client, plan]); db.flush()
        contract = Contract(academy_id=company.id, student_id=client.id, plan_id=plan.id, amount=plan.price, start_date=date.today(), due_day=10)
        db.add(contract); db.flush()
        for paid in (True, False):
            charge = Charge(academy_id=company.id, student_id=client.id, contract_id=contract.id,
                competence=date.today().strftime('%Y-%m') if paid else (date.today().replace(day=1)-timedelta(days=1)).strftime('%Y-%m'),
                due_date=date.today()-timedelta(days=1), original_amount=plan.price, amount=plan.price,
                paid=plan.price if paid else Decimal('0'), status='paga' if paid else 'pendente')
            db.add(charge); db.flush()
            if paid:
                db.add(Payment(academy_id=company.id, charge_id=charge.id, amount=charge.amount,
                    paid_at=date.today(), method='pix', idempotency_key='qa-fixture-payment'))
        for key, spec in CATALOG.items():
            db.add(Automation(academy_id=company.id, workflow_key=key, name=spec['name'], implemented=True))
        db.commit()
    uvicorn.run(app, host='127.0.0.1', port=8011, access_log=False)
