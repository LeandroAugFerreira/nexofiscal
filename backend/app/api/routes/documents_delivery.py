from fastapi import APIRouter,Depends,Header,HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import Invoice,EmailDelivery
from app.security.auth import require
from app.repositories.records import scoped,serialize,audit
from app.api.routes.business import operation_key
from app.fiscal.documents import pdf_document
from app.schemas.inputs import EmailDraftInput,EmailSendInput
from app.services.email_delivery import configuration,message_for,deliver

router=APIRouter(tags=["Documentos e entrega"])


@router.get('/invoices/{identity}/pdf')
def pdf(identity:int,download:bool=False,user=Depends(require('read')),db:Session=Depends(get_db)):
    invoice=scoped(db,Invoice,identity,user.academy_id)
    if not invoice.document_pdf:
        raise HTTPException(404,'Esta nota histórica possui apenas HTML. Emita uma nova simulação para gerar PDF.')
    content=pdf_document(invoice.document_snapshot,cancelled=True) if invoice.status=='cancelada' else invoice.document_pdf
    audit(db,user,'obter_pdf_simulado','notas_fiscais',identity);db.commit()
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'{"attachment" if download else "inline"}; filename="{invoice.identifier}-demonstracao.pdf"'})


@router.get('/invoices/{identity}/xml')
def xml(identity:int,user=Depends(require('read')),db:Session=Depends(get_db)):
    invoice=scoped(db,Invoice,identity,user.academy_id)
    if not invoice.document_xml:
        raise HTTPException(404,'XML demonstrativo não disponível para esta nota histórica.')
    audit(db,user,'obter_xml_simulado','notas_fiscais',identity);db.commit()
    return Response(invoice.document_xml,media_type='application/xml',headers={'Content-Disposition':f'attachment; filename="{invoice.identifier}-demonstracao.xml"'})


@router.get('/email/configuration')
def email_configuration(user=Depends(require('read'))):
    return configuration()


@router.get('/invoices/{identity}/email')
def history(identity:int,user=Depends(require('read')),db:Session=Depends(get_db)):
    scoped(db,Invoice,identity,user.academy_id)
    rows=db.scalars(select(EmailDelivery).where(EmailDelivery.invoice_id==identity,EmailDelivery.academy_id==user.academy_id).order_by(EmailDelivery.id.desc())).all()
    return {'configuration':configuration(),'items':[serialize(row) for row in rows]}


@router.post('/invoices/{identity}/email-draft')
def draft(identity:int,data:EmailDraftInput,user=Depends(require('fiscal')),db:Session=Depends(get_db)):
    invoice=scoped(db,Invoice,identity,user.academy_id)
    message=message_for(invoice,data.recipient)
    audit(db,user,'preparar_rascunho_email','notas_fiscais',identity);db.commit()
    return Response(message.as_bytes(),media_type='message/rfc822',headers={'Content-Disposition':f'attachment; filename="{invoice.identifier}-mensagem.eml"'})


@router.post('/invoices/{identity}/email-send',status_code=202)
def send(identity:int,data:EmailSendInput,idempotency_key:str=Header(default=''),user=Depends(require('email_send')),db:Session=Depends(get_db)):
    invoice=scoped(db,Invoice,identity,user.academy_id)
    return serialize(deliver(db,invoice,data.recipient,user,operation_key(idempotency_key)))
