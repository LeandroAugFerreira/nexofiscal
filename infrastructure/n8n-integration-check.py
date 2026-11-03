"""Teste ponta a ponta com n8n real, reutilizando documento simulado existente."""
import json
import os
from pathlib import Path
import sys
import uuid
import httpx
from sqlalchemy import select, func

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / 'backend'); sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.entities import Invoice, Payment, Charge, Student, EmailDelivery, User


def counts(db, company):
    return {model.__tablename__: db.scalar(select(func.count()).select_from(model).where(model.academy_id == company))
        for model in (Invoice, Payment, Charge, Student, EmailDelivery)}


def main():
    cfg = settings()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == cfg.demo_email.lower(), User.role == 'administrador'))
        invoice = db.scalar(select(Invoice).where(Invoice.academy_id == user.academy_id,
            Invoice.status == 'autorizada', Invoice.charge_id.is_not(None), Invoice.identifier.like('SIM-%')).order_by(Invoice.id))
        if not invoice or not invoice.document_pdf:
            raise RuntimeError('Não foi encontrada uma nota simulada com cobrança para o teste sem nova emissão.')
        before = counts(db, user.academy_id)
        payloads = {'payment-confirmed': {'charge_id': invoice.charge_id}, 'document-delivery': {'invoice_id': invoice.id},
            'due-reminders': {'days': 7}, 'failure-recovery': {}, 'monthly-closing': {}, 'alerts': {}}
        company = user.academy_id
    report = {'real_n8n': True, 'email_sent': False, 'new_invoice_created': False, 'checks': []}
    with httpx.Client(base_url='http://127.0.0.1:8010', timeout=60) as client:
        login = client.post('/api/auth/login', json={'email': cfg.demo_email, 'password': cfg.demo_admin_password or cfg.demo_password})
        if login.status_code != 200: raise RuntimeError('Login administrativo não confirmado.')
        client.headers['X-CSRF-Token'] = login.json()['csrf_token']
        data = client.get('/api/automations').json()
        if not data['connection']['connected']: raise RuntimeError('A API ainda não confirmou a conexão n8n.')
        if {row['workflow_key'] for row in data['workflows']} != set(payloads):
            raise RuntimeError('O cadastro não contém exatamente as seis rotinas esperadas.')
        for workflow in data['workflows']:
            key = workflow['workflow_key']
            if key not in payloads: continue
            path = f"/api/automations/{workflow['id']}/run?via=n8n"
            headers = {'Idempotency-Key': 'live-n8n-' + uuid.uuid4().hex + '-' + key}
            result = client.post(path, json=payloads[key], headers=headers)
            if result.status_code != 200:
                raise RuntimeError(f'Workflow {key}: HTTP {result.status_code}. Credenciais e resposta omitidas.')
            row = result.json()
            if row['status'] != 'sucesso' or row['source'] != 'n8n':
                raise RuntimeError(f'Workflow {key}: resultado não confirmado.')
            if key == 'payment-confirmed':
                repeated = client.post(path, json=payloads[key], headers=headers)
                if repeated.status_code != 200 or repeated.json()['id'] != row['id']:
                    raise RuntimeError('Proteção contra duplicidade não confirmada.')
            report['checks'].append({'key': key, 'run_id': row['id'], 'status': row['status'], 'source': row['source']})
            print('Ponta a ponta confirmado: ' + key)
        client.post('/api/auth/logout')
    with SessionLocal() as db:
        after = counts(db, company)
    if before != after: raise RuntimeError('Os totais de documentos/financeiro/e-mails mudaram durante a verificação.')
    report.update({'counts_before': before, 'counts_after': after, 'idempotency_verified': True})
    destination = ROOT / 'artifacts' / 'n8n-integration.json'
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Seis workflows confirmados no n8n real. Nenhuma nota nova, alteração financeira ou envio de e-mail.')


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print(str(error) if isinstance(error, RuntimeError) else f'Falha {type(error).__name__}; dados privados omitidos.', file=sys.stderr)
        raise SystemExit(1)
