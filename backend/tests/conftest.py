import os
from pathlib import Path

runtime = Path(__file__).parent / ".runtime"
runtime.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + (runtime / "tests.db").as_posix()
os.environ["DEMO_PASSWORD"] = "Tests-only-password-123"
os.environ["DEMO_EMAIL"] = "administrador@example.com"
os.environ["PORTFOLIO_ENABLED"] = "false"
os.environ["AUTOMATION_TOKEN"] = "test-automation-token-with-at-least-32-characters"
os.environ["N8N_WEBHOOK_URL"] = ""
os.environ["N8N_HEALTH_URL"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""

import pytest
from fastapi.testclient import TestClient
from app.database.session import Base, engine, SessionLocal
from app.models.entities import Academy, User, FiscalConfig
from app.security.auth import hasher, attempts
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    attempts.clear()
    with SessionLocal() as db:
        academy=Academy(name="Academia Teste",legal_name="Teste Ltda",cnpj="00000000000191")
        db.add(academy)
        db.flush()
        db.add(FiscalConfig(academy_id=academy.id))
        for role in ("administrador","recepcao","financeiro","contabilidade"):
            db.add(User(academy_id=academy.id,name=role,email=f"{role}@example.com",role=role,password_hash=hasher.hash("Tests-only-password-123")))
        db.commit()
    with TestClient(app) as c:
        yield c


def login(client, role="administrador"):
    response=client.post('/api/auth/login',json={"email":f"{role}@example.com","password":"Tests-only-password-123"})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf_token']
    return response.json()


@pytest.fixture
def authenticated(client):
    login(client)
    return client


@pytest.fixture
def financial(authenticated):
    c=authenticated
    s=c.post('/api/students',json={"name":"Ana Teste","cpf":"52998224725","email":"ana@example.com"})
    p=c.post('/api/plans',json={"name":"Musculação","price":"119.90"})
    assert s.status_code==p.status_code==201,(s.text,p.text)
    contract=c.post('/api/contracts',json={"student_id":s.json()['id'],"plan_id":p.json()['id'],"start_date":"2020-01-01","due_day":10})
    charge=c.post('/api/charges',json={"contract_id":contract.json()['id'],"competence":"2026-10","due_date":"2026-10-10"})
    assert contract.status_code==charge.status_code==201,(contract.text,charge.text)
    return c,s.json(),p.json(),contract.json(),charge.json()
