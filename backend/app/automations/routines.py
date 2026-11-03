"""Rotinas reais do demonstrador. Nenhuma rotina transmite e-mail ou NFS-e oficial."""
import hashlib
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models.entities import Automation, AutomationRun, Charge, Payment, Invoice, EmailDelivery, Student
from app.repositories.records import scoped, audit
from app.repositories.fiscal_queries import LOCAL_ZONE, invoice_query
from app.schemas.inputs import InvoiceInput
from app.services.fiscal import issue, demo_config
from app.services.email_delivery import message_for, configuration

CATALOG = {
    'payment-confirmed': {'name': 'Pagamento confirmado → emitir NFS-e', 'description': 'Valida uma cobrança quitada e gera o documento simulado sem duplicidade.', 'input': 'charge'},
    'document-delivery': {'name': 'Documento autorizado → preparar entrega', 'description': 'Confere o PDF e prepara os dados para baixar a mensagem. O envio de e-mail continua manual.', 'input': 'invoice'},
    'due-reminders': {'name': 'Vencimentos → preparar lembretes', 'description': 'Lista cobranças em aberto e prepara textos de lembrete para revisão, sem enviar mensagens.', 'input': 'days'},
    'failure-recovery': {'name': 'Falhas → diagnosticar pendências', 'description': 'Localiza rejeições e entregas com falha ou resultado desconhecido, sem repetir envios.', 'input': None},
    'monthly-closing': {'name': 'Fechamento mensal → consolidar resultados', 'description': 'Calcula previsto, recebido, saldo e situação fiscal do mês escolhido.', 'input': 'competence'},
    'alerts': {'name': 'Alertas → verificar operação', 'description': 'Apresenta avisos de cobranças, notas e configuração para consulta no sistema.', 'input': None},
}


def describe(row):
    spec = CATALOG.get(row.workflow_key)
    return {'name': spec['name'] if spec else row.name, 'implemented': bool(spec),
        'description': spec['description'] if spec else 'Rotina não disponível.',
        'input': spec['input'] if spec else None}


def _run(db, key, data, user):
    today = datetime.now(LOCAL_ZONE).date()
    if key == 'payment-confirmed':
        if not data.charge_id:
            raise HTTPException(422, 'Escolha uma cobrança integralmente paga.')
        charge = scoped(db, Charge, data.charge_id, user.academy_id)
        invoice = issue(db, InvoiceInput(charge_id=charge.id), user, f'automation-charge-{charge.id}')
        return {'message': 'Documento simulado disponível. Nenhum e-mail enviado.',
            'invoice_id': invoice.id, 'identifier': invoice.identifier, 'invoice_status': invoice.status,
            'links': [{'label': 'Abrir nota', 'path': f'/invoices/{invoice.id}'}]}
    if key == 'document-delivery':
        if not data.invoice_id:
            raise HTTPException(422, 'Escolha uma nota autorizada com PDF.')
        invoice = scoped(db, Invoice, data.invoice_id, user.academy_id)
        message = message_for(invoice)
        return {'message': 'PDF conferido e mensagem disponível para preparação. Nenhum e-mail enviado.',
            'invoice_id': invoice.id, 'identifier': invoice.identifier, 'subject': str(message['Subject']),
            'pdf_attached': True, 'email_sent': False,
            'links': [{'label': 'Abrir nota e opções de e-mail', 'path': f'/invoices/{invoice.id}'}]}
    if key == 'due-reminders':
        rows = db.scalars(select(Charge).where(Charge.academy_id == user.academy_id,
            Charge.status != 'cancelada', Charge.paid < Charge.amount,
            Charge.due_date <= today + timedelta(days=data.days)).order_by(Charge.due_date, Charge.id)).all()
        items = []
        for charge in rows[:100]:
            client = db.get(Student, charge.student_id)
            balance = format(charge.amount - charge.paid, '.2f')
            items.append({'charge_id': charge.id, 'client': client.name, 'due_date': str(charge.due_date),
                'balance': balance, 'text': f'Olá, {client.name}. A cobrança de R$ {balance.replace(".", ",")} tem vencimento em {charge.due_date.strftime("%d/%m/%Y")}. Este é um lembrete demonstrativo para revisão.'})
        return {'message': f'{len(rows)} cobrança(s) para conferência. Nenhum lembrete enviado.',
            'total': len(rows), 'items': items, 'email_sent': False,
            'links': [{'label': 'Consultar cobranças', 'path': '/charges'}]}
    if key == 'failure-recovery':
        invoices = db.scalars(select(Invoice).where(Invoice.academy_id == user.academy_id,
            Invoice.status == 'rejeitada').order_by(Invoice.id.desc())).all()
        latest = select(func.max(EmailDelivery.id)).where(EmailDelivery.academy_id == user.academy_id).group_by(EmailDelivery.invoice_id)
        deliveries = db.scalars(select(EmailDelivery).where(EmailDelivery.academy_id == user.academy_id, EmailDelivery.id.in_(latest),
            EmailDelivery.status.in_(['falhou', 'resultado_desconhecido'])).order_by(EmailDelivery.id.desc())).all()
        items = [{'type': 'Rejeição fiscal simulada', 'reference': x.identifier or f'Solicitação {x.id}',
            'path': f'/invoices/{x.id}', 'message': x.error or 'Consulte os dados antes de reprocessar.'} for x in invoices[:50]]
        items += [{'type': 'Entrega de e-mail', 'reference': f'Tentativa {x.id}', 'path': f'/invoices/{x.invoice_id}',
            'message': 'Confira a caixa de enviados antes de repetir.' if x.status == 'resultado_desconhecido' else x.message} for x in deliveries[:50]]
        return {'message': f'{len(invoices) + len(deliveries)} ocorrência(s) localizadas. Nenhum reprocessamento automático.',
            'total': len(invoices) + len(deliveries), 'items': items}
    if key == 'monthly-closing':
        competence = data.competence or today.strftime('%Y-%m')
        year, month = map(int, competence.split('-'))
        if year < 1900 or year > 9998:
            raise HTTPException(422, 'Escolha uma competência entre 1900 e 9998.')
        start = date(year, month, 1)
        following = date(year + (month == 12), month % 12 + 1, 1)
        charges = db.scalars(select(Charge).where(Charge.academy_id == user.academy_id,
            Charge.competence == competence, Charge.status != 'cancelada')).all()
        payments = db.scalars(select(Payment).where(Payment.academy_id == user.academy_id,
            Payment.paid_at >= start, Payment.paid_at < following)).all()
        invoices = db.scalars(invoice_query(user.academy_id, start=start, end=following-timedelta(days=1))).all()
        money = lambda values: format(sum(values, Decimal('0')), '.2f')
        return {'message': f'Consolidação de {competence} concluída. Registros originais preservados.',
            'competence': competence, 'totals': {
                'Previsto na competência': money(x.amount for x in charges),
                'Recebido no mês': money(x.amount for x in payments),
                'Saldo das cobranças do mês': money(x.amount-x.paid for x in charges),
                'Notas autorizadas': sum(x.status == 'autorizada' for x in invoices),
                'Notas rejeitadas': sum(x.status == 'rejeitada' for x in invoices),
                'Notas canceladas': sum(x.status == 'cancelada' for x in invoices)},
            'links': [{'label': 'Abrir relatórios', 'path': '/reports'}]}
    if key == 'alerts':
        overdue = db.scalars(select(Charge).where(Charge.academy_id == user.academy_id,
            Charge.due_date < today, Charge.status != 'cancelada', Charge.paid < Charge.amount)).all()
        rejected = db.scalars(select(Invoice).where(Invoice.academy_id == user.academy_id, Invoice.status == 'rejeitada')).all()
        items = []
        if overdue:
            items.append({'type': 'Financeiro', 'message': f'{len(overdue)} cobrança(s) vencida(s).', 'path': '/charges'})
        if rejected:
            items.append({'type': 'Fiscal', 'message': f'{len(rejected)} rejeição(ões) simulada(s).', 'path': '/invoices?status=rejeitada'})
        if not configuration()['configured']:
            items.append({'type': 'E-mail', 'message': 'Remetente SMTP ainda não configurado.', 'path': '/fiscal-config?tab=email'})
        return {'message': f'{len(items)} alerta(s) para conferência. Nenhuma notificação externa.', 'items': items, 'total': len(items)}
    raise HTTPException(404, 'Rotina não disponível.')


def execute(db, workflow, data, user, idempotency_key, source='local'):
    if workflow.workflow_key not in CATALOG:
        raise HTTPException(422, 'Esta rotina não está implementada.')
    if not workflow.enabled:
        raise HTTPException(409, 'Ative a rotina antes de executar.')
    fingerprint = hashlib.sha256(json.dumps(data.model_dump(mode='json'), sort_keys=True).encode()).hexdigest()
    previous = db.scalar(select(AutomationRun).where(AutomationRun.idempotency_key == idempotency_key))
    if previous:
        if previous.automation_id != workflow.id or previous.request_hash != fingerprint or previous.source != source:
            raise HTTPException(409, 'Chave de execução já utilizada com outros dados.')
        return previous
    # Confere o ambiente inclusive nas rotinas de consulta: nenhum adaptador oficial.
    demo_config(db, user.academy_id)
    try:
        with db.begin_nested():
            result = _run(db, workflow.workflow_key, data, user)
        status, message = 'sucesso', result['message']
    except HTTPException as error:
        if error.status_code == 404:
            raise
        result, status, message = {}, 'erro', str(error.detail)
    run = AutomationRun(automation_id=workflow.id, charge_id=data.charge_id if workflow.workflow_key == 'payment-confirmed' else None,
        status=status, message=message, result_data=result, source=source,
        idempotency_key=idempotency_key, request_hash=fingerprint)
    db.add(run); db.flush()
    audit(db, user, 'executar_rotina_' + source, 'automacoes', workflow.id, f'Execução {run.id}: {status}.')
    return run
