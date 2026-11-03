import json
from typing import Literal
from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import Automation
from app.repositories.records import scoped, serialize
from app.schemas.automations import AutomationExecution
from app.security.auth import require
from app.api.routes.business import operation_key, automation_user
from app.automations.routines import CATALOG, execute
from app.automations.workflows import export_workflow
from app.automations.integration import execute_via_n8n
from fastapi import HTTPException
from sqlalchemy import select

router = APIRouter(tags=['Rotinas e n8n'])


@router.post('/automations/{identity}/run')
def run_local(identity: int, data: AutomationExecution, via: Literal['local', 'n8n'] = 'local', idempotency_key: str = Header(default=''),
        user=Depends(require('automation')), db: Session = Depends(get_db)):
    workflow = scoped(db, Automation, identity, user.academy_id)
    key = operation_key(idempotency_key)
    run = execute_via_n8n(db, workflow, data, user, key) if via == 'n8n' else execute(db, workflow, data, user, key, source='local')
    db.commit()
    return serialize(run)


@router.get('/automations/{identity}/workflow')
def workflow_file(identity: int, target: Literal['local', 'docker'] = 'local',
        user=Depends(require('automation')), db: Session = Depends(get_db)):
    workflow = scoped(db, Automation, identity, user.academy_id)
    if workflow.workflow_key not in CATALOG:
        raise HTTPException(404, 'Workflow não disponível.')
    return Response(json.dumps(export_workflow(workflow.workflow_key, target), ensure_ascii=False, indent=2),
        media_type='application/json', headers={'Content-Disposition': f'attachment; filename="nexofiscal-{workflow.workflow_key}.json"'})


@router.post('/automation/run/{key}')
def run_from_n8n(key: str, data: AutomationExecution, idempotency_key: str = Header(default=''),
        user=Depends(automation_user), db: Session = Depends(get_db)):
    workflow = db.scalar(select(Automation).where(Automation.workflow_key == key, Automation.academy_id == user.academy_id))
    if not workflow:
        raise HTTPException(404, 'Rotina não cadastrada nesta empresa.')
    run = execute(db, workflow, data, user, operation_key(idempotency_key), source='n8n')
    db.commit()
    return serialize(run)
