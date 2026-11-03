from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func
from app.database.session import SessionLocal
from app.models.entities import Charge, Payment, Invoice, Student, Service, Academy, FiscalConfig, FiscalEvent
from conftest import login


def setup_service(c):
    return c.post('/api/services',json={'name':'Consultoria','price':'350.00'}).json()


def direct(c,client,service,key='direct-invoice-key',**changes):
    payload={'client_id':client['id'],'service_id':service['id'],'amount':'350.00','competence':date.today().strftime('%Y-%m'),'description':'Consultoria em gestão'}
    payload.update(changes)
    return c.post('/api/fiscal/issue-direct',headers={'Idempotency-Key':key},json=payload)


def test_pf_pj_registration_and_document_validation(authenticated):
    c=authenticated
    pf=c.post('/api/clients',json={'name':'Cliente PF','cpf':'52998224725'})
    pj=c.post('/api/clients',json={'name':'Cliente Empresa Ltda','person_type':'pj','cnpj':'11222333000181','trade_name':'Empresa Teste'})
    assert pf.status_code==pj.status_code==201,(pf.text,pj.text)
    assert pj.json()['cpf'] is None and pj.json()['person_type']=='pj'
    assert c.get(f"/api/clients/{pj.json()['id']}").json()['cnpj']=='11222333000181'
    assert c.post('/api/clients',json={'name':'Empresa duplicada','person_type':'pj','cnpj':'11222333000181'}).status_code==409
    assert c.post('/api/clients',json={'name':'CNPJ inválido','person_type':'pj','cnpj':'11111111111111'}).status_code==422
    assert c.post('/api/clients',json={'name':'Documento misturado','person_type':'pj','cpf':'52998224725','cnpj':'11222333000181'}).status_code==422
    assert c.post('/api/clients',json={'name':'Sem documento','person_type':'pf'}).status_code==422
    listing=c.get('/api/clients').json()['items']
    assert any(x['cnpj']=='**.***.***/****-81' for x in listing)


def test_direct_issue_preview_and_no_fictitious_finance(authenticated):
    c=authenticated
    client=c.post('/api/clients',json={'name':'Empresa Cliente','person_type':'pj','cnpj':'11222333000181'}).json()
    service=setup_service(c)
    payload={'client_id':client['id'],'service_id':service['id'],'amount':'350.00','competence':date.today().strftime('%Y-%m')}
    preview=c.post('/api/fiscal/preview',json=payload)
    assert preview.status_code==200 and preview.json()['client']['person_type']=='pj'
    assert len(preview.json()['checks'])==5 and all(x['passed'] for x in preview.json()['checks'])
    assert 'SEM VALIDADE FISCAL' in preview.json()['message']
    created=direct(c,client,service)
    assert created.status_code==201,created.text
    invoice=created.json()
    assert invoice['origin']=='avulsa' and invoice['charge_id'] is None
    assert invoice['identifier'].startswith('SIM-')
    doc=c.get(f"/api/invoices/{invoice['id']}/document")
    assert doc.status_code==200 and 'Empresa Cliente' in doc.text and 'SEM VALIDADE FISCAL' in doc.text
    overview=c.get('/api/fiscal/overview').json()
    assert overview['authorized']==1 and Decimal(overview['authorized_amount'])==Decimal('350.00')
    assert len(overview['events'])==3
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Charge))==0
        assert db.scalar(select(func.count()).select_from(Payment))==0
    assert c.get('/api/reports/invoices.csv').status_code==200
    assert c.get('/api/reports/invoices.csv?plan_id=123').status_code==200


def test_direct_idempotency_payload_and_rejection(authenticated):
    c=authenticated
    client=c.post('/api/clients',json={'name':'Cliente Teste','cpf':'52998224725'}).json()
    service=setup_service(c)
    first=direct(c,client,service,simulate_rejection=True)
    assert first.status_code==201 and first.json()['status']=='rejeitada'
    assert direct(c,client,service,simulate_rejection=True).json()['id']==first.json()['id']
    assert direct(c,client,service,amount='351.00',simulate_rejection=True).status_code==409
    retried=c.post(f"/api/invoices/{first.json()['id']}/retry")
    assert retried.status_code==200 and retried.json()['status']=='autorizada'
    assert c.post(f"/api/invoices/{first.json()['id']}/cancel",json={'reason':'Cancelamento do teste fiscal'}).status_code==200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice))==1


def test_direct_permissions_active_and_real_fiscal_block(authenticated):
    c=authenticated
    client=c.post('/api/clients',json={'name':'Cliente Teste','cpf':'52998224725'}).json()
    service=setup_service(c)
    assert direct(c,client,service,amount='0').status_code==422
    assert direct(c,client,service,amount='1.234').status_code==422
    c.delete(f"/api/services/{service['id']}")
    assert direct(c,client,service).status_code==422
    c.put(f"/api/services/{service['id']}",json={'name':'Consultoria','price':'350.00','status':'ativo'})
    c.post('/api/auth/logout')
    login(c,'recepcao')
    assert direct(c,client,service).status_code==403
    assert c.get('/api/fiscal/overview').status_code==200


def test_ready_charge_origin_still_requires_payment(financial):
    c,client,_,_,charge=financial
    assert c.get('/api/fiscal/ready-charges').json()['total']==0
    c.post('/api/payments',headers={'Idempotency-Key':'ready-payment-key'},json={'charge_id':charge['id'],'amount':charge['amount'],'paid_at':date.today().isoformat(),'method':'pix'})
    assert c.get('/api/fiscal/ready-charges').json()['total']==1
    c.post('/api/invoices',headers={'Idempotency-Key':'ready-invoice-key'},json={'charge_id':charge['id']})
    assert c.get('/api/fiscal/ready-charges').json()['total']==0
    assert c.get('/api/invoices?origin=cobranca').json()['total']==1
    assert c.get('/api/invoices?origin=avulsa').json()['total']==0


def test_direct_client_scope_and_search(authenticated):
    c=authenticated
    client=c.post('/api/clients',json={'name':'Cliente Teste','cpf':'52998224725'}).json()
    service=setup_service(c)
    invoice=direct(c,client,service).json()
    assert c.get('/api/invoices?q='+invoice['identifier']).json()['total']==1
    assert c.get('/api/invoices?q=Consultoria').json()['total']==1
    assert c.get('/api/clients/1/history').json()['invoices'][0]['id']==invoice['id']
    with SessionLocal() as db:
        company=Academy(name='Outra empresa',legal_name='Outra Ltda',cnpj='00000000000191')
        # CNPJ diferente da empresa inicial para manter unicidade.
        company.cnpj='11444777000161'
        db.add(company)
        db.flush()
        db.get(Student,client['id']).academy_id=company.id
        db.commit()
    assert direct(c,client,service,key='out-of-scope-key').status_code==404


def test_fiscal_period_local_day_shared_with_overview_and_csv(authenticated):
    c=authenticated
    client=c.post('/api/clients',json={'name':'Cliente Teste','cpf':'52998224725'}).json()
    service=setup_service(c)
    times=[datetime(2026,10,12,2,59,59),datetime(2026,10,12,3),
        datetime(2026,10,13,2,59,59),datetime(2026,10,13,3)]
    invoices=[]
    for i,instant in enumerate(times):
        row=direct(c,client,service,key=f'period-invoice-{i}',simulate_rejection=i==2,
            description='Consultoria no limite do dia').json()
        invoices.append(row)
        with SessionLocal() as db:
            db.get(Invoice,row['id']).created_at=instant
            db.commit()
    with SessionLocal() as db:
        company=Academy(name='Empresa externa',legal_name='Externa Ltda',cnpj='11444777000161')
        db.add(company);db.flush()
        outsider=Invoice(academy_id=company.id,student_id=client['id'],service_id=service['id'],
            amount=Decimal('999'),service_description='Consultoria externa',status='rejeitada',
            created_at=times[1],idempotency_key='period-outsider-key',origin='avulsa')
        db.add(outsider);db.flush()
        db.add(FiscalEvent(invoice_id=outsider.id,status='rejeitada',message='Evento externo'))
        db.commit()
    filters='start=2026-10-12&end=2026-10-12&origin=avulsa&q=Consultoria'
    listing=c.get('/api/invoices?'+filters).json()
    assert {x['id'] for x in listing['items']}=={invoices[1]['id'],invoices[2]['id']}
    overview=c.get('/api/fiscal/overview?'+filters).json()
    assert overview['total']==2 and overview['authorized']==1 and overview['rejected']==1
    assert overview['authorized_amount']=='350.00' and overview['rejection_rate']=='50.0'
    assert overview['period']['timezone']=='America/Sao_Paulo'
    assert {x['invoice_id'] for x in overview['events']}=={invoices[1]['id'],invoices[2]['id']}
    assert [x['id'] for x in overview['attention']]==[invoices[2]['id']]
    exported=c.get('/api/reports/invoices.csv?'+filters).text
    assert len(exported.strip().splitlines())==3
    assert invoices[1]['identifier'] in exported and invoices[0]['identifier'] not in exported
    empty=c.get('/api/fiscal/overview?'+filters+'&status=rejeitada').json()
    # A categoria escolhida na tabela não restringe a distribuição dos indicadores.
    assert empty['authorized']==1
    assert c.get('/api/fiscal/overview?'+filters.replace('avulsa','cobranca')).json()['total']==0
    assert c.get('/api/reports/invoices.csv?status=pendentes').text.strip().count('\n')==0
    for path in ('/api/invoices','/api/fiscal/overview','/api/reports/invoices.csv'):
        assert c.get(path+'?start=2026-10-13&end=2026-10-12').status_code==422


def test_portfolio_scenarios_readonly_fictitious_scoped_and_demo_only(authenticated):
    c=authenticated
    ordinary=c.post('/api/clients',json={'name':'Cliente real','cpf':'52998224725'}).json()
    c.post('/api/services',json={'name':'Serviço regular','price':'100'})
    assert not any(x['available'] for x in c.get('/api/fiscal/scenarios').json()['items'])
    pj=c.post('/api/clients',json={'name':'Empresa fictícia','person_type':'pj','cnpj':'11222333000181',
        'notes':'Cliente fictício para portfólio.'}).json()
    with SessionLocal() as db:
        db.get(Student,ordinary['id']).notes='Cliente fictício para demonstração.'
        db.add(Service(academy_id=1,name='Consultoria exemplo',price=Decimal('350'),description='Serviço fictício'))
        db.commit()
        before=db.scalar(select(func.count()).select_from(Invoice))
    response=c.get('/api/fiscal/scenarios')
    assert response.status_code==200
    examples=response.json()['items']
    assert all(x['available'] for x in examples)
    assert examples[1]['form']['client_id']==pj['id']
    assert examples[2]['form']['simulate_rejection'] is True
    assert not examples[0]['form']['simulate_rejection']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice))==before
        db.get(Student,pj['id']).status='inativo'
        db.commit()
    assert c.get('/api/fiscal/scenarios').json()['items'][1]['available'] is False
    with SessionLocal() as db:
        db.get(FiscalConfig,1).environment='producao'
        db.commit()
    assert c.get('/api/fiscal/scenarios').status_code==422
    c.post('/api/auth/logout');login(c,'recepcao')
    assert c.get('/api/fiscal/scenarios').status_code==403


def test_preflight_rechecks_stored_client_document(authenticated):
    c=authenticated
    client=c.post('/api/clients',json={'name':'Cliente Teste','cpf':'52998224725'}).json()
    service=setup_service(c)
    payload={'client_id':client['id'],'service_id':service['id'],'amount':'100','competence':'2026-10'}
    assert c.post('/api/fiscal/preview',json=payload).status_code==200
    with SessionLocal() as db:
        db.get(Student,client['id']).cpf='11111111111'
        db.commit()
    assert c.post('/api/fiscal/preview',json=payload).status_code==422
    assert direct(c,client,service).status_code==422


def test_charge_preflight_rechecks_stored_client_document(financial):
    c,client,_,_,charge=financial
    c.post('/api/payments',headers={'Idempotency-Key':'checklist-payment-key'},json={
        'charge_id':charge['id'],'amount':charge['amount'],'paid_at':date.today().isoformat(),'method':'pix'})
    assert c.get(f"/api/charges/{charge['id']}/eligibility").json()['eligible'] is True
    with SessionLocal() as db:
        db.get(Student,client['id']).cpf='11111111111'
        db.commit()
    response=c.get(f"/api/charges/{charge['id']}/eligibility").json()
    assert not response['eligible'] and 'CPF ou CNPJ do cliente inválido' in response['reasons']
    assert c.post('/api/invoices',headers={'Idempotency-Key':'checklist-charge-key'},json={'charge_id':charge['id']}).status_code==422
