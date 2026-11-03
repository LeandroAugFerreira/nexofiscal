"""Acrescenta representação moderna às simulações antigas, sem reescrever HTML original."""
import re
from html import unescape
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.entities import Invoice,Student
from app.fiscal.documents import snapshot,pdf_document,xml_document


def refresh():
    count=0
    with SessionLocal() as db:
        rows=db.scalars(select(Invoice).where(Invoice.identifier.is_not(None),Invoice.document_snapshot.is_(None))).all()
        for invoice in rows:
            data=snapshot(db,invoice,db.get(Student,invoice.student_id))
            original=invoice.document or ''
            match=re.search(r'<dt>(?:Cliente fictício / Tomador|Aluno fictício / Tomador|Aluno fictício / Tomador)</dt>\s*<dd>(.*?)</dd>',original,re.S)
            if match:data['client']['name']=unescape(re.sub(r'<[^>]+>','',match.group(1)))
            data['historical_reconstruction']=True
            data['historical_notice']='Representação de uma simulação histórica. Valor, descrição e identificação originais preservados; dados adicionais de emitente e contato complementados pelos cadastros disponíveis.'
            invoice.document_snapshot=data
            invoice.document_pdf=pdf_document(data)
            invoice.document_xml=xml_document(data)
            count+=1
        db.commit()
    print(f'{count} documentos históricos ganharam representação PDF/XML; HTML original preservado.')


if __name__=='__main__':refresh()
