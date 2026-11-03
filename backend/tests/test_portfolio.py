from app.core.config import settings
from app.portfolio import provision
from app.database.session import SessionLocal
from app.models.entities import FiscalConfig


def test_portfolio_is_hidden_when_disabled(client):
    assert client.get('/api/auth/portfolio').json()=={'enabled':False}


def test_portfolio_login_and_immediate_disable(client,monkeypatch):
    cfg=settings()
    monkeypatch.setattr(cfg,'portfolio_enabled',True)
    provision()
    credentials=client.get('/api/auth/portfolio').json()
    assert credentials=={'enabled':True,'email':cfg.portfolio_email,'password':cfg.portfolio_password}
    assert credentials['email']!=cfg.demo_email and credentials['password']!=cfg.demo_password
    response=client.post('/api/auth/login',json={k:credentials[k] for k in ('email','password')})
    assert response.status_code==200 and response.json()['role']=='portfolio'
    assert client.get('/api/users').status_code==200
    assert client.get('/api/insights/users').status_code==200
    monkeypatch.setattr(cfg,'portfolio_enabled',False)
    assert client.get('/api/auth/me').status_code==401
    assert client.get('/api/auth/portfolio').json()=={'enabled':False}
    assert client.post('/api/auth/login',json={k:credentials[k] for k in ('email','password')}).status_code==403


def test_portfolio_blocked_outside_demonstration(client,monkeypatch):
    cfg=settings()
    monkeypatch.setattr(cfg,'portfolio_enabled',True)
    provision()
    with SessionLocal() as db:
        fiscal=db.get(FiscalConfig,1)
        fiscal.environment='producao'
        db.commit()
    assert client.get('/api/auth/portfolio').json()=={'enabled':False}
    assert client.post('/api/auth/login',json={'email':cfg.portfolio_email,'password':cfg.portfolio_password}).status_code==403
