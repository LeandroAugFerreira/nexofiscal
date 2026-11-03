import smtplib
import ssl
import socket
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, formatdate
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models.entities import EmailDelivery
from app.repositories.records import audit


def configuration():
    cfg=settings()
    configured=bool(cfg.smtp_host and cfg.smtp_username and cfg.smtp_password and cfg.smtp_from_email and cfg.smtp_port in (465,587))
    return {"configured":configured,"sender":cfg.smtp_from_email or None,"sender_name":cfg.smtp_from_name,
        "message":"Credenciais SMTP configuradas; autenticação é verificada ao enviar" if configured else "Configure a senha de app do Gmail no backend para habilitar envio real"}


def authenticate(connection, cfg):
    # LOGIN por desafio permite identificar a recusa do Gmail sem ativar debug SMTP.
    methods = getattr(connection, 'esmtp_features', {}).get('auth', '').upper().split()
    if cfg.smtp_host.lower() == 'smtp.gmail.com' and 'LOGIN' in methods:
        connection.user, connection.password = cfg.smtp_username, cfg.smtp_password
        connection.auth('LOGIN', connection.auth_login, initial_response_ok=False)
    else:
        connection.login(cfg.smtp_username, cfg.smtp_password)


def message_for(invoice,recipient=""):
    if invoice.status!="autorizada" or not invoice.document_pdf:
        raise HTTPException(422,"Envio disponível apenas para documento simulado autorizado com PDF.")
    cfg=settings();data=invoice.document_snapshot
    message=EmailMessage()
    message['Subject']=f"[DEMONSTRAÇÃO] Documento de serviço {invoice.identifier} | NexoFiscal"
    if cfg.smtp_from_email:
        message['From']=formataddr((cfg.smtp_from_name,cfg.smtp_from_email))
    if recipient:
        message['To']=str(recipient)
    message['Date']=formatdate(localtime=False)
    message['Message-ID']=make_msgid(domain='nexofiscal.local')
    message.set_content(f"Olá, {data['client']['name']}.\n\nSegue o documento demonstrativo {invoice.identifier}, referente ao serviço:\n{data['description']}\n\nValor documentado: R$ {data['amount'].replace('.',',')}\nCompetência: {data['competence']}\n\nDOCUMENTO SIMULADO - SEM VALIDADE FISCAL.\nEste PDF faz parte de uma demonstração de portfólio. Não houve emissão ou autorização governamental.\n\nAtenciosamente,\n{data['issuer'].get('legal_name') or data['issuer']['name']}\nGerado pelo NexoFiscal\n")
    message.add_attachment(invoice.document_pdf,maintype='application',subtype='pdf',filename=f'{invoice.identifier}-demonstracao.pdf')
    return message


def deliver(db,invoice,recipient,user,key):
    previous=db.scalar(select(EmailDelivery).where(EmailDelivery.idempotency_key==key))
    if previous:
        if previous.academy_id!=user.academy_id or previous.invoice_id!=invoice.id or previous.recipient!=str(recipient):
            raise HTTPException(409,"Chave de envio já usada com outros dados.")
        return previous
    domain=str(recipient).split('@')[-1].lower()
    if domain.endswith(('.example.com','.example.org','.example.net','.invalid','.test')) or domain in ('example.com','example.org','example.net'):
        raise HTTPException(422,"O endereço é demonstrativo. Informe uma caixa de e-mail real.")
    message=message_for(invoice,recipient)
    cfg=settings()
    if not configuration()['configured']:
        raise HTTPException(503,"Gmail não configurado. Insira a senha de app localmente e reinicie o backend.")
    row=EmailDelivery(academy_id=user.academy_id,invoice_id=invoice.id,user_id=user.id,recipient=str(recipient),subject=str(message['Subject']),idempotency_key=key,status='preparando')
    db.add(row);db.flush();audit(db,user,'preparar_envio_email','notas_fiscais',invoice.id);db.commit()
    try:
        if cfg.smtp_port==465:
            connection=smtplib.SMTP_SSL(cfg.smtp_host,cfg.smtp_port,timeout=15,context=ssl.create_default_context())
            connection.ehlo()
        else:
            connection=smtplib.SMTP(cfg.smtp_host,cfg.smtp_port,timeout=15)
            connection.ehlo();connection.starttls(context=ssl.create_default_context());connection.ehlo()
        try:
            authenticate(connection,cfg)
            row.status='enviando';db.commit()
            refused=connection.send_message(message)
            if refused:
                row.status='falhou';row.message='O servidor recusou o destinatário.'
            else:
                row.status='aceita_smtp';row.message='Mensagem aceita pelo servidor SMTP. A chegada à caixa de entrada não foi confirmada.'
        finally:
            try:connection.quit()
            except (smtplib.SMTPException,OSError):pass
    except smtplib.SMTPAuthenticationError:
        row.status='falhou';row.message='O Gmail recusou a conta ou a senha de app. Gere uma senha de app na conta remetente e atualize a configuração local. A mensagem não foi enviada.'
    except smtplib.SMTPRecipientsRefused:
        row.status='falhou';row.message='Destinatário recusado pelo servidor.'
    except smtplib.SMTPServerDisconnected:
        if row.status=='enviando':
            row.status='resultado_desconhecido';row.message='A conexão SMTP foi encerrada durante o envio. Consulte a caixa de enviados antes de tentar novamente.'
        else:
            row.status='falhou';row.message='A conexão SMTP foi encerrada antes do envio. Verifique a autenticação e a conexão com o provedor. A mensagem não foi enviada.'
    except (smtplib.SMTPException,OSError,socket.timeout):
        row.status='resultado_desconhecido' if row.status=='enviando' else 'falhou'
        row.message='Falha na comunicação. Consulte a caixa de enviados antes de tentar novamente.'
    audit(db,user,'resultado_envio_email','notas_fiscais',invoice.id,row.status)
    db.commit()
    return row
