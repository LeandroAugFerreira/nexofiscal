"""Provisiona os seis workflows na instalação n8n local. Não imprime credenciais."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
import httpx

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / 'backend')
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import settings
from app.automations.routines import CATALOG
from app.automations.workflows import export_workflow

MANIFEST = ROOT / '.runtime' / 'n8n-workflows.json'
EDITOR = 'http://127.0.0.1:5678'


def request(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    if not response.is_success:
        raise RuntimeError(f'{method} {path}: HTTP {response.status_code}. Resposta e credenciais omitidas.')
    result = response.json()
    return result.get('data', result) if isinstance(result, dict) else result


def main():
    cfg = settings()
    if cfg.n8n_editor_url != EDITOR:
        raise RuntimeError('Este assistente só provisiona a instalação local dedicada ao projeto.')
    password = cfg.demo_admin_password or cfg.demo_password
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'workflows': {}}
    def save():
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    with httpx.Client(base_url=EDITOR, timeout=45, headers={'Origin': EDITOR, 'browser-id': str(uuid.uuid4())}) as client:
        info = request(client, 'GET', '/rest/settings')
        management = info.get('userManagement', {})
        if management.get('showSetupOnFirstLoad', management.get('showSetUpOnFirstLoad', False)):
            request(client, 'POST', '/rest/owner/setup', json={'email': cfg.demo_email, 'password': password,
                'firstName': 'Administrador', 'lastName': 'NexoFiscal'})
            print('Proprietário local criado com o acesso administrativo do projeto.')
        else:
            request(client, 'POST', '/rest/login', json={'emailOrLdapLoginId': cfg.demo_email, 'password': password})
        credential_body = {'name': 'NexoFiscal Internal Token', 'type': 'httpHeaderAuth',
            'data': {'name': 'X-Automation-Token', 'value': cfg.automation_token}}
        if manifest.get('credential_id'):
            credential = request(client, 'PATCH', '/rest/credentials/' + manifest['credential_id'], json=credential_body)
        else:
            credential = request(client, 'POST', '/rest/credentials', json=credential_body)
            manifest['credential_id'] = credential['id']; save()
        for key in CATALOG:
            definition = export_workflow(key, 'local')
            for node in definition['nodes']:
                if 'credentials' in node:
                    node['credentials']['httpHeaderAuth'] = {'id': manifest['credential_id'], 'name': 'NexoFiscal Internal Token'}
            # A publicação fica em chamada separada; nunca envia segredos em arquivos JSON.
            definition.pop('active', None)
            digest = hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()
            previous = manifest['workflows'].get(key)
            if previous:
                current = request(client, 'GET', '/rest/workflows/' + previous['id'])
                if previous.get('definition_hash') != digest:
                    body = dict(definition)
                    if current.get('checksum'): body['expectedChecksum'] = current['checksum']
                    current = request(client, 'PATCH', '/rest/workflows/' + previous['id'], json=body)
            else:
                current = request(client, 'POST', '/rest/workflows', json=definition)
                manifest['workflows'][key] = {'id': current['id']}; save()
            if not current.get('active') or previous is None or previous.get('definition_hash') != digest:
                body = {'versionId': current['versionId']}
                if current.get('checksum'): body['expectedChecksum'] = current['checksum']
                current = request(client, 'POST', '/rest/workflows/' + current['id'] + '/activate', json=body)
            manifest['workflows'][key] = {'id': current['id'], 'definition_hash': digest, 'published': True}
            save(); print('Workflow publicado: ' + key)
        manifest['editor'] = EDITOR
        package = ROOT / '.runtime' / 'n8n' / 'node_modules' / 'n8n' / 'package.json'
        manifest['version'] = json.loads(package.read_text(encoding='utf-8'))['version']
        save()
    with httpx.Client(base_url='http://127.0.0.1:8010', timeout=15) as api:
        login = request(api, 'POST', '/api/auth/login', json={'email': cfg.demo_email, 'password': password})
        api.headers['X-CSRF-Token'] = login['csrf_token']
        workflows = request(api, 'GET', '/api/automations')['workflows']
        for workflow in workflows:
            if workflow['workflow_key'] in CATALOG and not workflow['enabled']:
                request(api, 'PATCH', f"/api/automations/{workflow['id']}", json={'enabled': True})
        request(api, 'POST', '/api/auth/logout')
    print('Seis rotinas habilitadas e publicadas. Nenhum e-mail enviado.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error) if isinstance(error, RuntimeError) else f'Falha {type(error).__name__}; dados e credenciais omitidos.', file=sys.stderr)
        raise SystemExit(1)
