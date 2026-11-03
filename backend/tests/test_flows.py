from datetime import date
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.models.entities import Payment, Invoice, Student, Contract, Audit, Academy, User
from app.database.session import SessionLocal
from conftest import login


def pay(c,charge,amount="119.90",key="payment-key-0001"):
    return c.post('/api/payments',headers={'Idempotency-Key':key},json={"charge_id":charge['id'],"amount":amount,"paid_at":date.today().isoformat(),"method":"pix"})


def issue(c,charge,reject=False,key="invoice-key-0001"):
    return c.post('/api/invoices',headers={'Idempotency-Key':key},json={"charge_id":charge['id'],"simulate_rejection":reject})


def test_login_csrf_logout(client):
    assert client.get('/api/students').status_code==401
    assert client.post('/api/auth/login',json={"email":"administrador@example.com","password":"wrong"}).status_code==401
    user=login(client)
    assert client.get('/api/auth/me').json()['role']=='administrador'
    assert client.post('/api/students',headers={'X-CSRF-Token':'wrong'},json={"name":"Teste","cpf":"52998224725"}).status_code==403
    assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/dashboard').status_code==401


def test_validation_and_catalog(authenticated):
    c=authenticated
    assert c.post('/api/students',json={"name":"Teste","cpf":"11111111111"}).status_code==422
    first=c.post('/api/students',json={"name":"Teste Aluno","cpf":"52998224725"})
    assert first.status_code==201
    assert c.post('/api/students',json={"name":"Duplicado","cpf":"52998224725"}).status_code==409
    assert c.get('/api/students').json()['items'][0]['cpf']=='***.***.***-25'
    assert c.get(f"/api/students/{first.json()['id']}").json()['cpf']=='52998224725'
    assert c.put(f"/api/students/{first.json()['id']}",json={"name":"Aluno Editado","cpf":"52998224725"}).status_code==200
    service=c.post('/api/services',json={"name":"Personal trainer","price":"80.00"})
    assert service.status_code==201
    assert c.put(f"/api/services/{service.json()['id']}",json={"name":"Personal Editado","price":"90.00"}).json()['price']=='90.00'
    assert c.delete(f"/api/services/{service.json()['id']}").json()['status']=='inativo'
    assert c.post('/api/plans',json={"name":"Decimal inválido","price":"12.345"}).status_code==422
    assert c.put('/api/academy',json={"name":"Academia","legal_name":"Teste Ltda","cnpj":"11111111111111"}).status_code==422


def test_snapshot_duplicates_inactivation(financial):
    c,student,plan,contract,charge=financial
    assert c.put(f"/api/plans/{plan['id']}",json={"name":"Musculação","price":"200.00"}).status_code==200
    assert c.get('/api/contracts').json()['items'][0]['amount']=='119.90'
    duplicate=c.post('/api/charges',json={"contract_id":contract['id'],"competence":"2026-10","due_date":"2026-10-10"})
    assert duplicate.status_code==409
    assert c.delete(f"/api/students/{student['id']}").status_code==200
    with SessionLocal() as db:
        assert db.get(Student,student['id']).status=='inativo'
        assert db.get(Contract,contract['id'])


def test_payment_partial_idempotency_and_overpayment(financial):
    c,_,_,_,charge=financial
    assert pay(c,charge,'20.10').status_code==201
    assert pay(c,charge,'20.10').status_code==201
    assert pay(c,charge,'21.10').status_code==409
    assert pay(c,charge,'100.00','payment-overflow').status_code==422
    current=c.get('/api/charges').json()['items'][0]
    assert current['paid']=='20.10' and current['balance']=='99.80' and current['status']=='parcialmente_paga'
    assert issue(c,charge).status_code==422
    assert pay(c,charge,'99.80','payment-completion').status_code==201
    assert c.get('/api/charges').json()['items'][0]['status']=='paga'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Payment))==2


def test_fiscal_lifecycle_and_document(financial):
    c,_,_,_,charge=financial
    assert pay(c,charge).status_code==201
    first=issue(c,charge,True)
    assert first.status_code==201 and first.json()['status']=='rejeitada'
    identity=first.json()['id']
    assert issue(c,charge).json()['id']==identity
    assert issue(c,charge,key='another-invoice-key').json()['id']==identity
    retry=c.post(f'/api/invoices/{identity}/retry')
    assert retry.status_code==200 and retry.json()['identifier'].startswith('SIM-')
    document=c.get(f'/api/invoices/{identity}/document')
    assert 'DOCUMENTO SIMULADO — SEM VALIDADE FISCAL' in document.text
    assert c.post(f'/api/invoices/{identity}/cancel',json={'reason':'Cancelamento para teste'}).json()['status']=='cancelada'
    assert 'SIMULAÇÃO CANCELADA' in c.get(f'/api/invoices/{identity}/document').text
    assert c.post(f'/api/invoices/{identity}/retry').status_code==409
    events=c.get(f'/api/invoices/{identity}').json()['events']
    assert [x['status'] for x in events]==['aguardando_emissao','processando','rejeitada','processando','autorizada','cancelamento_solicitado','cancelada']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice))==1
        assert db.get(Invoice,identity).document


def test_rbac_and_real_fiscal_block(financial):
    c,_,_,_,charge=financial
    assert pay(c,charge).status_code==201
    identity=issue(c,charge).json()['id']
    assert c.put('/api/fiscal-config',json={'environment':'producao','provider':'simulador'}).status_code==422
    c.post('/api/auth/logout')
    login(c,'recepcao')
    assert c.get('/api/students').status_code==200
    assert pay(c,charge,key='forbidden-payment').status_code==403
    assert c.get('/api/audit').status_code==403
    assert c.get('/api/users').status_code==403
    assert c.post(f'/api/invoices/{identity}/cancel',json={'reason':'Motivo de teste adequado'}).status_code==403


def test_dashboard_reports_and_persistence(financial):
    c,_,_,_,charge=financial
    pay(c,charge)
    issue(c,charge)
    dashboard=c.get('/api/dashboard').json()
    assert Decimal(dashboard['received'])==Decimal('119.90')
    assert Decimal(dashboard['balance'])==0 and dashboard['authorized_invoices']==1
    assert c.get('/api/insights/students').status_code==200
    assert c.get('/api/search?q=Ana').json()
    report=c.get('/api/reports/payments.csv')
    assert report.status_code==200 and 'Ana Teste' in report.text
    assert c.get('/api/reports/charges.csv?start=2026-01-01&end=2025-01-01').status_code==422
    with SessionLocal() as db:
        assert db.scalar(select(Payment)).amount==Decimal('119.90')
        assert db.scalar(select(Audit).where(Audit.action=='exportar_csv'))


def test_webhook_auth_and_idempotency(financial):
    c,_,_,_,charge=financial
    pay(c,charge)
    assert c.post(f"/api/automation/issue/{charge['id']}").status_code==401
    headers={'X-Automation-Token':'test-automation-token-with-at-least-32-characters'}
    assert c.get(f"/api/automation/charges/{charge['id']}",headers=headers).json()['eligible']
    first=c.post(f"/api/automation/issue/{charge['id']}",headers=headers)
    second=c.post(f"/api/automation/issue/{charge['id']}",headers=headers)
    assert first.json()['id']==second.json()['id']
    assert first.json()['simulated'] is True


def test_concurrent_payments_cannot_overpay(financial):
    c,_,_,_,charge=financial
    cookies=dict(c.cookies)
    csrf=c.headers['X-CSRF-Token']
    def worker(key):
        with TestClient(app) as other:
            other.cookies.update(cookies)
            other.headers['X-CSRF-Token']=csrf
            return pay(other,charge,'80.00',key).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(worker,['concurrency-key-one','concurrency-key-two']))
    assert sorted(statuses)==[201,422]
    assert c.get('/api/charges').json()['items'][0]['paid']=='80.00'


def test_cross_academy_access(financial):
    c,student,_,_,_=financial
    with SessionLocal() as db:
        other=Academy(name='Outra',legal_name='Outra Teste',cnpj='11222333000181')
        db.add(other)
        db.flush()
        user=db.scalar(select(User).where(User.role=='administrador'))
        user.academy_id=other.id
        db.commit()
    assert c.get(f"/api/students/{student['id']}").status_code==404
    assert c.get(f"/api/students/{student['id']}/history").status_code==404
    assert c.get('/api/students').json()['total']==0


def test_admin_insights_no_secrets_and_origin_block(authenticated):
    c=authenticated
    assert c.get('/api/insights/users').status_code==200
    users=c.get('/api/users').json()
    assert all('password_hash' not in x for x in users)
    assert any(x['last_login'] for x in users)
    assert len(c.get('/api/fiscal-config').json()['metrics'])==4
    assert len(c.get('/api/automations').json()['metrics'])==4
    assert c.post('/api/auth/login',headers={'Origin':'https://unauthorized.example'},json={'email':'administrador@example.com','password':'Tests-only-password-123'}).status_code==403


def test_concurrent_emission_persists_only_one_invoice(financial):
    c,_,_,_,charge=financial
    assert pay(c,charge).status_code==201
    cookies=dict(c.cookies)
    csrf=c.headers['X-CSRF-Token']
    def worker(key):
        with TestClient(app) as other:
            other.cookies.update(cookies)
            other.headers['X-CSRF-Token']=csrf
            return issue(other,charge,key=key).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(worker,['concurrent-invoice-one','concurrent-invoice-two']))
    assert 201 in statuses and set(statuses)<={201,409}
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice))==1
