from io import BytesIO
import pytest
from email import policy
from email.parser import BytesParser
from pypdf import PdfReader
from sqlalchemy import select,func
from app.database.session import SessionLocal
from app.models.entities import Invoice,EmailDelivery,Student
from app.core.config import settings
from app.portfolio import provision
from app.services import email_delivery
from conftest import login


def create_invoice(c):
    client=c.post('/api/clients',json={'name':'Cliente Documento','cpf':'52998224725'}).json()
    service=c.post('/api/services',json={'name':'Consultoria empresarial','price':'350.00'}).json()
    created=c.post('/api/fiscal/issue-direct',headers={'Idempotency-Key':'document-example-key'},json={'client_id':client['id'],'service_id':service['id'],'amount':'350.00','competence':'2026-10','description':'Consultoria de processos e planejamento empresarial'})
    assert created.status_code==201,created.text
    return client,created.json()


def test_pdf_xml_and_immutable_snapshot(authenticated):
    c=authenticated;client,invoice=create_invoice(c)
    assert invoice['has_pdf'] and invoice['has_xml']
    response=c.get(f"/api/invoices/{invoice['id']}/pdf")
    assert response.status_code==200 and response.content.startswith(b'%PDF-')
    reader=PdfReader(BytesIO(response.content));text=' '.join(p.extract_text() for p in reader.pages)
    assert len(reader.pages)==1 and 'NexoFiscal' in text and 'SEM VALIDADE FISCAL' in text
    assert 'PRESTADOR' in text and 'TOMADOR' in text and 'TRIBUTAÇÃO' in text
    xml=c.get(f"/api/invoices/{invoice['id']}/xml")
    assert xml.status_code==200 and 'urn:nexofiscal:demonstracao' in xml.text and 'semValidadeFiscal="true"' in xml.text
    c.put(f"/api/clients/{client['id']}",json={'name':'Cliente Nome Alterado','cpf':'52998224725'})
    assert c.get(f"/api/invoices/{invoice['id']}/pdf").content==response.content
    with SessionLocal() as db:
        assert db.get(Invoice,invoice['id']).document_snapshot['client']['name']=='Cliente Documento'
    c.post(f"/api/invoices/{invoice['id']}/cancel",json={'reason':'Cancelamento demonstrativo para validar PDF'})
    cancelled=c.get(f"/api/invoices/{invoice['id']}/pdf")
    assert 'CANCELADA' in ''.join(p.extract_text() for p in PdfReader(BytesIO(cancelled.content)).pages)


def test_email_message_has_pdf_and_simulation_notice(authenticated):
    c=authenticated;_,invoice=create_invoice(c)
    response=c.post(f"/api/invoices/{invoice['id']}/email-draft",json={'recipient':'cliente.nfse.portifolio@gmail.com'})
    assert response.status_code==200
    message=BytesParser(policy=policy.default).parsebytes(response.content)
    assert '[DEMONSTRAÇÃO]' in message['Subject'] and 'NexoFiscal' in message['Subject']
    assert 'SEM VALIDADE FISCAL' in message.get_body(preferencelist=('plain',)).get_content()
    attachments=list(message.iter_attachments())
    assert len(attachments)==1 and attachments[0].get_content_type()=='application/pdf'
    assert attachments[0].get_payload(decode=True).startswith(b'%PDF-')
    assert not c.get('/api/email/configuration').json()['configured']
    assert c.post(f"/api/invoices/{invoice['id']}/email-send",headers={'Idempotency-Key':'mail-unconfigured'},json={'recipient':'cliente.nfse.portifolio@gmail.com'}).status_code==503


def configure(monkeypatch):
    cfg=settings()
    for key,value in {'smtp_host':'smtp.gmail.com','smtp_port':465,'smtp_username':'remetente@gmail.com','smtp_password':'test-app-password','smtp_from_email':'remetente@gmail.com'}.items():monkeypatch.setattr(cfg,key,value)


def test_smtp_acceptance_idempotency_and_no_secret_leak(authenticated,monkeypatch):
    c=authenticated;_,invoice=create_invoice(c);configure(monkeypatch)
    calls=[]
    class FakeSMTP:
        def __init__(self,*args,**kwargs):assert kwargs['context'].check_hostname
        def ehlo(self):return (250,b'ok')
        def login(self,*args):return (235,b'ok')
        def send_message(self,message):calls.append(message);return {}
        def quit(self):return (221,b'bye')
    monkeypatch.setattr(email_delivery.smtplib,'SMTP_SSL',FakeSMTP)
    path=f"/api/invoices/{invoice['id']}/email-send";headers={'Idempotency-Key':'mail-confirmed-test'};body={'recipient':'cliente.nfse.portifolio@gmail.com'}
    first=c.post(path,headers=headers,json=body);second=c.post(path,headers=headers,json=body)
    assert first.status_code==second.status_code==202 and first.json()['status']=='aceita_smtp'
    assert len(calls)==1 and first.json()['id']==second.json()['id']
    assert 'test-app-password' not in c.get('/api/email/configuration').text and 'test-app-password' not in first.text
    assert c.post(path,headers=headers,json={'recipient':'outro@gmail.com'}).status_code==409
    assert c.post(path,headers={'Idempotency-Key':'invalid-demo-recipient'},json={'recipient':'cliente@demo.example.com'}).status_code==422


def test_starttls_before_authentication_and_send(authenticated,monkeypatch):
    c=authenticated;_,invoice=create_invoice(c);configure(monkeypatch)
    monkeypatch.setattr(settings(),'smtp_port',587)
    calls=[]
    class FakeSTARTTLS:
        def __init__(self,host,port,**kwargs):
            assert host=='smtp.gmail.com' and port==587
            calls.append('connect')
        def ehlo(self):calls.append('ehlo')
        def starttls(self,context):
            assert context.check_hostname and context.verify_mode==email_delivery.ssl.CERT_REQUIRED
            calls.append('starttls')
        def login(self,*args):
            assert calls==['connect','ehlo','starttls','ehlo']
            calls.append('login')
        def send_message(self,message):
            assert calls[-1]=='login'
            calls.append('send');return {}
        def quit(self):calls.append('quit')
    monkeypatch.setattr(email_delivery.smtplib,'SMTP',FakeSTARTTLS)
    response=c.post(f"/api/invoices/{invoice['id']}/email-send",headers={'Idempotency-Key':'mail-starttls-test'},
        json={'recipient':'cliente.nfse.portifolio@gmail.com'})
    assert response.status_code==202 and response.json()['status']=='aceita_smtp'
    assert calls==['connect','ehlo','starttls','ehlo','login','send','quit']


def test_unknown_smtp_result_is_not_automatically_repeated(authenticated,monkeypatch):
    c=authenticated;_,invoice=create_invoice(c);configure(monkeypatch)
    calls=[]
    class TimeoutSMTP:
        def __init__(self,*args,**kwargs):pass
        def ehlo(self):return (250,b'ok')
        def login(self,*args):return (235,b'ok')
        def send_message(self,message):calls.append(1);raise OSError('private technical details')
        def quit(self):pass
    monkeypatch.setattr(email_delivery.smtplib,'SMTP_SSL',TimeoutSMTP)
    path=f"/api/invoices/{invoice['id']}/email-send";kwargs={'headers':{'Idempotency-Key':'mail-unknown-test'},'json':{'recipient':'cliente.nfse.portifolio@gmail.com'}}
    first=c.post(path,**kwargs);second=c.post(path,**kwargs)
    assert first.json()['status']=='resultado_desconhecido' and len(calls)==1
    assert 'private technical details' not in first.text


@pytest.mark.parametrize('rejected',[False,True])
def test_gmail_login_challenge_and_safe_authentication_failure(authenticated,monkeypatch,rejected):
    c=authenticated;_,invoice=create_invoice(c);configure(monkeypatch)
    sent=[]
    class FakeGoogleSMTP:
        esmtp_features={'auth':'LOGIN PLAIN XOAUTH2'}
        def __init__(self,*args,**kwargs):assert kwargs['context'].check_hostname
        def ehlo(self):return (250,b'ok')
        def login(self,*args):raise AssertionError('Gmail deve usar LOGIN por desafio quando anunciado.')
        def auth_login(self,challenge=None):return self.user if challenge is None else self.password
        def auth(self,method,auth_object,initial_response_ok):
            assert method=='LOGIN' and not initial_response_ok
            assert self.user=='remetente@gmail.com' and self.password=='test-app-password'
            if rejected:
                raise email_delivery.smtplib.SMTPAuthenticationError(535,b'5.7.8 private technical response')
            return (235,b'ok')
        def send_message(self,message):sent.append(1);return {}
        def quit(self):return (221,b'bye')
    monkeypatch.setattr(email_delivery.smtplib,'SMTP_SSL',FakeGoogleSMTP)
    response=c.post(f"/api/invoices/{invoice['id']}/email-send",headers={'Idempotency-Key':'gmail-login-challenge-test'},
        json={'recipient':'cliente.nfse.portifolio@gmail.com'})
    assert response.status_code==202
    result=response.json()
    assert result['status']==('falhou' if rejected else 'aceita_smtp')
    assert len(sent)==(0 if rejected else 1)
    assert 'test-app-password' not in response.text and 'private technical response' not in response.text
    if rejected:
        assert 'senha de app' in result['message'] and 'A mensagem não foi enviada' in result['message']


def test_public_portfolio_cannot_send_real_mail(client,monkeypatch):
    cfg=settings();monkeypatch.setattr(cfg,'portfolio_enabled',True);provision()
    result=client.post('/api/auth/login',json={'email':cfg.portfolio_email,'password':cfg.portfolio_password})
    client.headers['X-CSRF-Token']=result.json()['csrf_token']
    _,invoice=create_invoice(client)
    assert client.post(f"/api/invoices/{invoice['id']}/email-send",headers={'Idempotency-Key':'portfolio-mail-key'},json={'recipient':'cliente.nfse.portifolio@gmail.com'}).status_code==403
    assert client.post(f"/api/invoices/{invoice['id']}/email-draft",json={}).status_code==200


@pytest.mark.parametrize('role', ['administrador', 'financeiro', 'recepcao', 'contabilidade', 'portfolio'])
def test_email_send_permission_for_each_role(authenticated, monkeypatch, role):
    c = authenticated
    _, invoice = create_invoice(c)
    configure(monkeypatch)
    sent = []
    class FakeSMTP:
        def __init__(self, *args, **kwargs): pass
        def ehlo(self): return (250, b'ok')
        def login(self, *args): return (235, b'ok')
        def send_message(self, message): sent.append(message); return {}
        def quit(self): return (221, b'bye')
    monkeypatch.setattr(email_delivery.smtplib, 'SMTP_SSL', FakeSMTP)
    if role == 'portfolio':
        cfg = settings()
        monkeypatch.setattr(cfg, 'portfolio_enabled', True)
        provision()
        result = c.post('/api/auth/login', json={'email': cfg.portfolio_email, 'password': cfg.portfolio_password})
        assert result.status_code == 200
        c.headers['X-CSRF-Token'] = result.json()['csrf_token']
    else:
        login(c, role)
    response = c.post(f"/api/invoices/{invoice['id']}/email-send",
        headers={'Idempotency-Key': 'email-permission-test-' + role}, json={'recipient': 'cliente.nfse.portifolio@gmail.com'})
    authorized = role in ('administrador', 'financeiro')
    assert response.status_code == (202 if authorized else 403)
    assert len(sent) == (1 if authorized else 0)
    if authorized:
        assert response.json()['status'] == 'aceita_smtp'
