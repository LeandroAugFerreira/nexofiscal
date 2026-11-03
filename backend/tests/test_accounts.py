from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.database.session import SessionLocal
from app.models.entities import Academy, User, AuthSession, Audit, FiscalConfig
from app.security.auth import hasher, password_matches
from app.core.config import settings
from conftest import login


PASSWORD = "Account-test-password-123"


def data(**changes):
    return {"name": "Pessoa de Teste", "email": "pessoa@example.com", "role": "financeiro",
        "active": True, "password": PASSWORD, **changes}


def test_create_and_login_with_assigned_permissions(authenticated):
    c = authenticated
    response = c.post('/api/users', json=data(email="PESSOA@EXAMPLE.COM"))
    assert response.status_code == 201, response.text
    assert response.json()['email'] == 'pessoa@example.com'
    assert not {'password', 'password_hash'} & response.json().keys()
    with SessionLocal() as db:
        row = db.get(User, response.json()['id'])
        assert password_matches(row.password_hash, PASSWORD)
        assert db.scalar(select(Audit).where(Audit.action == 'criar_usuario', Audit.entity_id == row.id))
    result = c.post('/api/auth/login', json={"email": "pessoa@example.com", "password": PASSWORD})
    assert result.status_code == 200
    assert result.json()['role'] == 'financeiro'
    assert 'email_send' in result.json()['permissions']
    assert 'users' not in result.json()['permissions']


def test_duplicate_invalid_and_unauthorized_creation(client):
    assert client.post('/api/users', json=data()).status_code == 401
    login(client, 'financeiro')
    assert client.post('/api/users', json=data()).status_code == 403
    login(client)
    assert client.post('/api/users', json=data(email="ADMINISTRADOR@EXAMPLE.COM")).status_code == 409
    for invalid in ({'password': 'xY4!z'}, {'role': 'portfolio'}, {'name': '  '}, {'email': 'bad-email'}, {'academy_id': 99}):
        response = client.post('/api/users', json=data(**invalid))
        assert response.status_code == 422
        assert PASSWORD not in response.text
        assert 'xY4!z' not in response.text


def test_csrf_required_for_account_writes(authenticated):
    authenticated.headers.pop('X-CSRF-Token')
    assert authenticated.post('/api/users', json=data()).status_code == 403


def test_update_password_role_and_status_revokes_sessions(authenticated):
    c = authenticated
    row = c.post('/api/users', json=data()).json()
    with TestClient(app) as other:
        assert other.post('/api/auth/login', json={'email': row['email'], 'password': PASSWORD}).status_code == 200
        updated = c.put(f"/api/users/{row['id']}", json=data(role='recepcao', password='Replacement-password-123'))
        assert updated.status_code == 200, updated.text
        assert other.get('/api/auth/me').status_code == 401
        assert other.post('/api/auth/login', json={'email': row['email'], 'password': PASSWORD}).status_code == 401
        signed = other.post('/api/auth/login', json={'email': row['email'], 'password': 'Replacement-password-123'})
        assert signed.status_code == 200 and 'email_send' not in signed.json()['permissions']
        values = data(role='recepcao', active=False)
        values.pop('password')
        assert c.put(f"/api/users/{row['id']}", json=values).status_code == 200
        assert other.get('/api/auth/me').status_code == 401
        assert other.post('/api/auth/login', json={'email': row['email'], 'password': 'Replacement-password-123'}).status_code == 401
        assert c.put(f"/api/users/{row['id']}", json={**values, 'active': True}).status_code == 200
        assert other.post('/api/auth/login', json={'email': row['email'], 'password': 'Replacement-password-123'}).status_code == 200


def test_tenant_scope_and_self_protection(authenticated):
    c = authenticated
    own = c.get('/api/auth/me').json()
    assert c.put(f"/api/users/{own['id']}", json=data(email=own['email'], active=False)).status_code == 403
    assert c.put('/api/users/999999', json=data()).status_code == 404
    with SessionLocal() as db:
        company = Academy(name='Outra empresa', legal_name='Outra Ltda', cnpj='11222333000181')
        db.add(company); db.flush()
        row = User(academy_id=company.id, name='Outra pessoa', email='outra@example.com', role='administrador', password_hash=hasher.hash(PASSWORD))
        db.add(row); db.commit(); identity = row.id
    assert c.put(f'/api/users/{identity}', json=data()).status_code == 404
    assert all(row['id'] != identity for row in c.get('/api/users').json())


def test_own_profile_requires_password_and_preserves_role(authenticated):
    c = authenticated
    before = c.get('/api/auth/me').json()
    payload = {'name': 'Novo Nome', 'email': 'NOVO@EXAMPLE.COM', 'current_password': 'incorrect-password'}
    assert c.put('/api/auth/me', json=payload).status_code == 400
    assert c.get('/api/auth/me').json()['name'] == before['name']
    assert c.put('/api/auth/me', json={**payload, 'role': 'financeiro'}).status_code == 422
    result = c.put('/api/auth/me', json={**payload, 'current_password': 'Tests-only-password-123'})
    assert result.status_code == 200, result.text
    assert result.json()['role'] == before['role']
    assert result.json()['email'] == 'novo@example.com'
    assert result.json()['csrf_token'] != before['csrf_token']
    c.headers['X-CSRF-Token'] = result.json()['csrf_token']
    assert c.get('/api/auth/me').json()['name'] == 'Novo Nome'
    assert c.post('/api/auth/logout').status_code == 200
    assert c.post('/api/auth/login', json={'email': 'novo@example.com', 'password': 'Tests-only-password-123'}).status_code == 200


def test_change_own_password_rotates_session_and_preserves_spaces(authenticated):
    c = authenticated
    with TestClient(app) as other:
        login(other)
        original = c.get('/api/auth/me').json()
        payload = {'current_password': 'Tests-only-password-123', 'new_password': ' Spaces-kept-123 '}
        assert c.put('/api/auth/password', json={**payload, 'current_password': 'incorrect'}).status_code == 400
        assert c.put('/api/auth/password', json={**payload, 'new_password': payload['current_password']}).status_code == 400
        response = c.put('/api/auth/password', json=payload)
        assert response.status_code == 200, response.text
        assert response.json()['csrf_token'] != original['csrf_token']
        assert other.get('/api/auth/me').status_code == 401
        assert other.post('/api/auth/login', json={'email': 'administrador@example.com', 'password': 'Spaces-kept-123'}).status_code == 401
        assert other.post('/api/auth/login', json={'email': 'administrador@example.com', 'password': payload['new_password']}).status_code == 200
    with SessionLocal() as db:
        details = ' '.join(row.details for row in db.scalars(select(Audit)))
        assert payload['new_password'] not in details and payload['current_password'] not in details


def test_public_portfolio_cannot_manage_or_change_accounts(authenticated, monkeypatch):
    c = authenticated
    cfg = settings()
    monkeypatch.setattr(cfg, 'portfolio_enabled', True)
    with SessionLocal() as db:
        company = db.scalar(select(Academy))
        demo = User(academy_id=company.id, name='Portfólio', email=cfg.portfolio_email.lower(), role='portfolio', password_hash=hasher.hash(cfg.portfolio_password))
        db.add(demo); db.commit(); identity = demo.id
    assert c.put(f'/api/users/{identity}', json=data()).status_code == 403
    result = c.post('/api/auth/login', json={'email': cfg.portfolio_email, 'password': cfg.portfolio_password})
    assert result.status_code == 200
    c.headers['X-CSRF-Token'] = result.json()['csrf_token']
    assert c.get('/api/users').status_code == 200
    assert c.post('/api/users', json=data()).status_code == 403
    assert c.put('/api/users/1', json=data()).status_code == 403
    assert c.put('/api/auth/me', json={'name': 'Changed', 'email': 'changed@example.com', 'current_password': cfg.portfolio_password}).status_code == 403
    assert c.put('/api/auth/password', json={'current_password': cfg.portfolio_password, 'new_password': PASSWORD}).status_code == 403
