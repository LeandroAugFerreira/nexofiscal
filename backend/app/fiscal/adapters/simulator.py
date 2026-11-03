from app.fiscal.adapters.base import FiscalAdapter
from app.fiscal.documents import WATERMARK, snapshot, html_document, pdf_document, xml_document


class SimuladorFiscalAdapter(FiscalAdapter):
    def emitir_nota(self,invoice,student,reject=False,db=None):
        if reject:
            invoice.status="rejeitada"
            invoice.error="Rejeição simulada solicitada pelo operador. Nenhuma transmissão fiscal ocorreu."
            return
        if db is None:
            raise ValueError("A geração de documento exige os dados persistidos do emitente")
        invoice.identifier=f"SIM-{invoice.created_at.year}-{invoice.id:06d}"
        invoice.status="autorizada"
        invoice.error=None
        invoice.document_snapshot=snapshot(db,invoice,student)
        invoice.document=html_document(invoice.document_snapshot)
        invoice.document_pdf=pdf_document(invoice.document_snapshot)
        invoice.document_xml=xml_document(invoice.document_snapshot)

    def consultar_nota(self,invoice):
        return {"status":invoice.status,"identifier":invoice.identifier,"simulated":True}

    def cancelar_nota(self,invoice,reason):
        invoice.status="cancelada"

    def obter_documento(self,invoice):
        if invoice.document_snapshot:
            return html_document(invoice.document_snapshot,cancelled=invoice.status=="cancelada")
        if invoice.status=="cancelada" and invoice.document:
            return invoice.document.replace('<h1>FitNota / Demonstração</h1>','<h1>FitNota / Demonstração</h1><p class="warning">SIMULAÇÃO CANCELADA - registro histórico</p>')
        return invoice.document

    def verificar_conexao(self):
        return {"connected":True,"provider":"simulador","environment":"demonstracao","message":"Simulador NexoFiscal disponível"}
