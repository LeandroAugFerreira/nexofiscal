"""Servidor de QA local: banco temporário, contas fictícias e SMTP desabilitado."""
import os
import sys
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
temporary = root / '.tmp'
temporary.mkdir(exist_ok=True)
os.environ.update({
    'DATABASE_URL': 'sqlite:///' + (temporary / f'accounts-qa-{uuid4().hex}.db').as_posix(),
    'PORTFOLIO_ENABLED': 'true', 'PORTFOLIO_EMAIL': 'portfolio@example.com',
    'PORTFOLIO_PASSWORD': 'Accounts-QA-portfolio-123',
    'SMTP_HOST': '', 'SMTP_USERNAME': '', 'SMTP_PASSWORD': '', 'SMTP_FROM_EMAIL': '',
    'N8N_WEBHOOK_URL': '', 'N8N_HEALTH_URL': '', 'COOKIE_SECURE': 'false',
})
sys.path.insert(0, str(root / 'backend'))
from app.database.session import Base, engine, SessionLocal
from app.models.entities import Academy, FiscalConfig, User
from app.security.auth import hasher
from app.main import app
import uvicorn

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        company = Academy(name='Empresa QA', legal_name='Empresa fictícia de QA', cnpj='00000000000191')
        db.add(company); db.flush()
        db.add(FiscalConfig(academy_id=company.id))
        for name, email, role, password in [
            ('Administrador QA', 'admin@example.com', 'administrador', 'Accounts-QA-admin-123'),
            ('Portfólio QA', 'portfolio@example.com', 'portfolio', 'Accounts-QA-portfolio-123'),
        ]:
            db.add(User(academy_id=company.id, name=name, email=email, role=role, password_hash=hasher.hash(password)))
        db.commit()
    uvicorn.run(app, host='127.0.0.1', port=8011, access_log=False)
