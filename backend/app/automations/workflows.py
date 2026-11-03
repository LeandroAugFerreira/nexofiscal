from app.automations.routines import CATALOG


def export_workflow(key, target='local'):
    spec = CATALOG[key]
    base = 'http://backend:8000' if target == 'docker' else 'http://127.0.0.1:8010'
    credential = {'httpHeaderAuth': {'name': 'NexoFiscal Internal Token'}}
    webhook_path = 'fitnota-payment' if key == 'payment-confirmed' else 'nexofiscal-' + key
    return {
        'name': 'NexoFiscal — ' + spec['name'], 'active': False,
        'settings': {'executionOrder': 'v1', 'saveDataSuccessExecution': 'none', 'saveDataErrorExecution': 'none'},
        'nodes': [
            {'id': 'webhook', 'name': 'Receber solicitação', 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2,
                'position': [0, 0], 'webhookId': 'nexofiscal-' + key,
                'parameters': {'httpMethod': 'POST', 'path': webhook_path, 'authentication': 'headerAuth',
                    'responseMode': 'lastNode', 'options': {}}, 'credentials': credential},
            {'id': 'run', 'name': 'Executar rotina no NexoFiscal', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2,
                'position': [280, 0], 'parameters': {'method': 'POST', 'url': base + '/api/automation/run/' + key,
                    'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth',
                    'sendHeaders': True, 'headerParameters': {'parameters': [{'name': 'Idempotency-Key',
                        'value': '={{ $json.headers["idempotency-key"] || ("n8n-" + $execution.id + "-' + key + '") }}'}]},
                    'sendBody': True, 'specifyBody': 'json', 'jsonBody': '={{ JSON.stringify({ charge_id: $json.body.charge_id, invoice_id: $json.body.invoice_id, competence: $json.body.competence, days: $json.body.days }) }}',
                    'options': {'timeout': 30000}}, 'credentials': credential},
            {'id': 'notice', 'name': 'Configuração e limites', 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1,
                'position': [0, -270], 'parameters': {'content': '## NexoFiscal — demonstração\n' + spec['description'] +
                    '\nConfigure a credencial Header Auth NexoFiscal Internal Token (X-Automation-Token) nos dois nodes. Ative a rotina no sistema. Não envia e-mails nem documentos fiscais oficiais.',
                    'width': 620, 'height': 220}},
        ],
        'connections': {'Receber solicitação': {'main': [[{'node': 'Executar rotina no NexoFiscal', 'type': 'main', 'index': 0}]]}},
    }
