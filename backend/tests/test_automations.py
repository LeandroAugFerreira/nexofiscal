from datetime import date, timedelta
import pytest
from sqlalchemy import select, func
from app.database.session import SessionLocal
from app.models.entities import Automation, AutomationRun, Invoice, Charge, Payment, Academy, User, EmailDelivery
from app.automations.routines import CATALOG
from conftest import login


def provision():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == 'administrador'))
        for key, spec in CATALOG.items():
            db.add(Automation(academy_id=user.academy_id, workflow_key=key, name=spec['name'], implemented=True))
        db.commit()


def activate(c, key):
    row = next(x for x in c.get('/api/automations').json()['workflows'] if x['workflow_key'] == key)
    assert c.patch(f"/api/automations/{row['id']}", json={'enabled': True}).status_code == 200
    return row


def run(c, row, payload=None, key=None):
    return c.post(f"/api/automations/{row['id']}/run", json=payload or {}, headers={'Idempotency-Key': key or 'routine-' + row['workflow_key']})


def pay(c, charge):
    result = c.post('/api/payments', headers={'Idempotency-Key': 'routine-payment-test'},
        json={'charge_id': charge['id'], 'amount': charge['amount'], 'paid_at': date.today().isoformat(), 'method': 'pix'})
    assert result.status_code == 201


def test_catalog_activation_and_no_secret_leak(authenticated):
    c = authenticated
    provision()
    data = c.get('/api/automations').json()
    assert len(data['workflows']) == 6
    assert all(x['implemented'] and not x['enabled'] and x['description'] for x in data['workflows'])
    assert data['connection']['token_configured']
    assert 'test-automation-token-with-at-least-32-characters' not in str(data)
    row = data['workflows'][0]
    assert run(c, row).status_code == 409
    c.headers.pop('X-CSRF-Token')
    assert c.patch(f"/api/automations/{row['id']}", json={'enabled': True}).status_code == 403


def test_payment_routine_idempotency_and_invoice_history(financial):
    c, _, _, _, charge = financial
    provision(); pay(c, charge)
    row = activate(c, 'payment-confirmed')
    first = run(c, row, {'charge_id': charge['id']})
    assert first.status_code == 200, first.text
    result = first.json()
    assert result['status'] == 'sucesso' and result['source'] == 'local'
    assert result['result_data']['identifier'].startswith('SIM-')
    assert run(c, row, {'charge_id': charge['id']}).json()['id'] == result['id']
    assert run(c, row, {'charge_id': charge['id']}, 'another-routine-key').json()['result_data']['invoice_id'] == result['result_data']['invoice_id']
    assert run(c, row, {'charge_id': charge['id']+1}).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1
        assert db.scalar(select(func.count()).select_from(Payment)) == 1
    history = c.get('/api/automations').json()['runs']
    assert history[0]['result_data']['invoice_id'] == result['result_data']['invoice_id']


def test_delivery_prepares_without_smtp(financial, monkeypatch):
    c, _, _, _, charge = financial
    provision(); pay(c, charge)
    invoice = c.post('/api/invoices', headers={'Idempotency-Key': 'routine-invoice-test'}, json={'charge_id': charge['id']}).json()
    import app.services.email_delivery as delivery
    def forbidden(*args, **kwargs): raise AssertionError('Rotinas não devem conectar ao SMTP.')
    monkeypatch.setattr(delivery.smtplib, 'SMTP_SSL', forbidden)
    monkeypatch.setattr(delivery.smtplib, 'SMTP', forbidden)
    row = activate(c, 'document-delivery')
    result = run(c, row, {'invoice_id': invoice['id']}).json()
    assert result['status'] == 'sucesso'
    assert result['result_data']['pdf_attached'] and result['result_data']['email_sent'] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(EmailDelivery)) == 0


def test_read_routines_and_monthly_totals_do_not_change_finance(financial):
    c, _, _, _, charge = financial
    provision()
    with SessionLocal() as db:
        row = db.get(Charge, charge['id'])
        row.due_date = date.today() - timedelta(days=1)
        row.competence = date.today().strftime('%Y-%m')
        db.commit()
    for key in ('due-reminders', 'failure-recovery', 'monthly-closing', 'alerts'):
        row = activate(c, key)
        result = run(c, row).json()
        assert result['status'] == 'sucesso', result
        if key == 'due-reminders':
            assert result['result_data']['total'] == 1
            assert result['result_data']['items'][0]['charge_id'] == charge['id']
            assert result['result_data']['email_sent'] is False
        elif key == 'monthly-closing':
            assert result['result_data']['totals']['Previsto na competência'] == charge['amount']
            assert result['result_data']['totals']['Recebido no mês'] == '0.00'
        elif key == 'failure-recovery':
            assert result['result_data']['total'] == 0
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 0
        assert db.scalar(select(func.count()).select_from(Payment)) == 0
        assert db.get(Charge, charge['id']).paid == 0


def test_failure_diagnosis_uses_latest_delivery(financial):
    c, _, _, _, charge = financial
    provision(); pay(c, charge)
    invoice = c.post('/api/invoices', headers={'Idempotency-Key': 'diagnosis-invoice-test'}, json={'charge_id': charge['id']}).json()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == 'administrador'))
        for index, status in enumerate(('falhou', 'aceita_smtp')):
            db.add(EmailDelivery(academy_id=user.academy_id, user_id=user.id, invoice_id=invoice['id'],
                recipient='test@example.com', subject='Demonstração', status=status, idempotency_key=f'diagnosis-email-{index}', message='Estado de teste'))
        db.commit()
    row = activate(c, 'failure-recovery')
    assert run(c, row).json()['result_data']['total'] == 0


def test_permission_and_company_boundaries(authenticated):
    c = authenticated
    provision()
    row = activate(c, 'alerts')
    login(c, 'recepcao')
    assert run(c, row).status_code == 403
    assert c.get(f"/api/automations/{row['id']}/workflow").status_code == 403
    login(c)
    with SessionLocal() as db:
        company = Academy(name='Outra empresa', legal_name='Outra Ltda', cnpj='11222333000181')
        db.add(company); db.flush()
        user = db.scalar(select(User).where(User.role == 'administrador'))
        user.academy_id = company.id; db.commit()
    assert run(c, row).status_code == 404
    assert c.get(f"/api/automations/{row['id']}/workflow").status_code == 404
    assert c.get('/api/automations').json()['runs'] == []


def test_n8n_token_and_export(authenticated):
    c = authenticated
    provision()
    row = activate(c, 'alerts')
    assert c.post('/api/automation/run/alerts', json={}).status_code == 401
    result = c.post('/api/automation/run/alerts', json={}, headers={
        'X-Automation-Token': 'test-automation-token-with-at-least-32-characters', 'Idempotency-Key': 'n8n-execution-123'})
    assert result.status_code == 200 and result.json()['source'] == 'n8n'
    for target in ('local', 'docker'):
        response = c.get(f"/api/automations/{row['id']}/workflow?target={target}")
        assert response.status_code == 200
        workflow = response.json()
        assert not workflow['active']
        assert len(workflow['nodes']) == 3 and workflow['connections']
        assert 'test-automation-token-with-at-least-32-characters' not in response.text
        assert ('127.0.0.1:8010' if target == 'local' else 'backend:8000') in response.text
        assert workflow['nodes'][0]['parameters']['authentication'] == 'headerAuth'


def test_invalid_input_records_failure_without_invoice(financial):
    c, _, _, _, charge = financial
    provision()
    row = activate(c, 'payment-confirmed')
    result = run(c, row, {'charge_id': charge['id']}).json()
    assert result['status'] == 'erro' and 'paga' in result['message']
    assert run(c, row, {'charge_id': 999999}, 'not-found-charge-key').status_code == 404
    assert run(c, row, {'charge_id': charge['id'], 'password': 'no-credentials-allowed'}).status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 0
        assert db.scalar(select(func.count()).select_from(AutomationRun)) == 1


@pytest.mark.parametrize('as_array', [False, True])
def test_browser_executes_through_n8n_and_reuses_result(authenticated, monkeypatch, as_array):
    import httpx
    from app.core.config import settings
    from app.automations import integration
    c = authenticated
    provision()
    row = activate(c, 'alerts')
    monkeypatch.setattr(settings(), 'n8n_webhook_url', 'http://127.0.0.1:5678/webhook/fitnota-payment')
    calls = []
    class FakeN8n:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, headers, json):
            calls.append(url)
            assert url.endswith('/webhook/nexofiscal-alerts')
            response = c.post('/api/automation/run/alerts', json=json, headers=headers)
            assert response.status_code == 200
            return httpx.Response(200, json=[response.json()] if as_array else response.json())
    monkeypatch.setattr(integration.httpx, 'Client', FakeN8n)
    path = f"/api/automations/{row['id']}/run?via=n8n"
    first = c.post(path, json={}, headers={'Idempotency-Key': 'browser-n8n-execution-test'})
    second = c.post(path, json={}, headers={'Idempotency-Key': 'browser-n8n-execution-test'})
    assert first.status_code == second.status_code == 200, first.text
    assert first.json()['source'] == 'n8n' and first.json()['status'] == 'sucesso'
    assert first.json()['id'] == second.json()['id'] and len(calls) == 1


def test_n8n_unconfigured_or_unconfirmed_response(authenticated, monkeypatch):
    import httpx
    from app.core.config import settings
    from app.automations import integration
    c = authenticated
    provision()
    row = activate(c, 'alerts')
    path = f"/api/automations/{row['id']}/run?via=n8n"
    headers = {'Idempotency-Key': 'unconfirmed-n8n-test'}
    assert c.post(path, json={}, headers=headers).status_code == 503
    monkeypatch.setattr(settings(), 'n8n_webhook_url', 'http://127.0.0.1:5678/webhook/fitnota-payment')
    class FakeN8n:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return httpx.Response(200, json={'id': 99999})
    monkeypatch.setattr(integration.httpx, 'Client', FakeN8n)
    assert c.post(path, json={}, headers=headers).status_code == 502
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AutomationRun)) == 0
