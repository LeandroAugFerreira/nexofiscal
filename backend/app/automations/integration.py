import httpx
import hashlib
import json
from urllib.parse import urlsplit
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models.entities import Automation, AutomationRun


def connection():
    cfg = settings()
    checks = {'health_configured': bool(cfg.n8n_health_url), 'webhook_configured': bool(cfg.n8n_webhook_url),
        'token_configured': len(cfg.automation_token) >= 32}
    editor = urlsplit(cfg.n8n_editor_url)
    if editor.scheme in ('http', 'https') and editor.hostname and not editor.username and not editor.password:
        checks['editor_url'] = cfg.n8n_editor_url
    if not cfg.n8n_health_url:
        return {"connected": False, "configured": False, "message": "n8n não configurado", **checks}
    try:
        with httpx.Client(timeout=3) as client:
            response = client.get(cfg.n8n_health_url)
        return {"connected": response.is_success, "configured": True,
            "message": "n8n disponível" if response.is_success else "n8n indisponível", **checks}
    except httpx.HTTPError:
        return {"connected": False, "configured": True, "message": "Sem conexão com n8n", **checks}


def dispatch(db, charge, academy_id):
    workflow = db.scalar(select(Automation).where(Automation.workflow_key == "payment-confirmed", Automation.academy_id == academy_id))
    if not workflow:
        raise HTTPException(503, "Workflow demonstrativo não cadastrado. Aplique o seed.")
    run = AutomationRun(automation_id=workflow.id, charge_id=charge.id)
    db.add(run)
    cfg = settings()
    if not workflow.enabled:
        run.status, run.message = "ignorada", "Workflow desativado no NexoFiscal"
    elif not cfg.n8n_webhook_url or len(cfg.automation_token) < 32:
        run.status, run.message = "erro", "Configure URL e token de integração no backend"
    else:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(cfg.n8n_webhook_url, headers={"X-Automation-Token": cfg.automation_token},
                    json={"charge_id": charge.id, "event": "payment.manual_registered", "simulated": True})
            run.status = "encaminhada" if response.is_success else "erro"
            run.message = "Evento recebido pelo webhook; consulte o histórico fiscal" if response.is_success else f"Webhook retornou HTTP {response.status_code}"
        except httpx.HTTPError:
            run.status, run.message = "erro", "Falha de comunicação; consulte a nota antes de repetir"
    db.flush()
    return run


def execute_via_n8n(db, workflow, data, user, key):
    cfg = settings()
    if not workflow.enabled:
        raise HTTPException(409, 'Ative a rotina antes de executar.')
    if not cfg.n8n_webhook_url or len(cfg.automation_token) < 32:
        raise HTTPException(503, 'A conexão com o n8n ainda não está configurada.')
    fingerprint = hashlib.sha256(json.dumps(data.model_dump(mode='json'), sort_keys=True).encode()).hexdigest()
    previous = db.scalar(select(AutomationRun).where(AutomationRun.idempotency_key == key))
    if previous:
        if previous.automation_id != workflow.id or previous.request_hash != fingerprint or previous.source != 'n8n':
            raise HTTPException(409, 'Chave de execução já utilizada com outros dados.')
        return previous
    url = cfg.n8n_webhook_url if workflow.workflow_key == 'payment-confirmed' else cfg.n8n_webhook_url.rsplit('/', 1)[0] + '/nexofiscal-' + workflow.workflow_key
    try:
        with httpx.Client(timeout=40) as client:
            response = client.post(url, headers={'X-Automation-Token': cfg.automation_token, 'Idempotency-Key': key},
                json=data.model_dump(mode='json'))
    except httpx.HTTPError:
        raise HTTPException(502, 'Falha na comunicação com o n8n. Consulte o histórico antes de tentar novamente.') from None
    if not response.is_success:
        raise HTTPException(502, f'O n8n retornou HTTP {response.status_code}. Confira se o workflow está publicado e autenticado.')
    try:
        result = response.json()
        if isinstance(result, list) and len(result) == 1:
            result = result[0]
        identity = result.get('id') if isinstance(result, dict) else None
    except ValueError:
        identity = None
    run = db.scalar(select(AutomationRun).where(AutomationRun.idempotency_key == key,
        AutomationRun.automation_id == workflow.id, AutomationRun.source == 'n8n'))
    if not run or run.id != identity or run.request_hash != fingerprint:
        raise HTTPException(502, 'O n8n respondeu sem confirmar o resultado da rotina. Consulte o histórico.')
    return run
