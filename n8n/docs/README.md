# Rotinas e integração n8n — NexoFiscal

## Instalação local gerenciada no Windows

O projeto pode manter sua própria instalação em `.runtime`: Node `v24.22.0` e n8n `2.43.7`, sem alterar o Node global. O instalador valida o SHA-256 do runtime com a distribuição oficial do Node. `.runtime` e os dados privados não são versionados.

Para preparar uma nova cópia:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infrastructure\instalar-n8n.ps1
backend\.venv\Scripts\python.exe infrastructure\n8n-local.py configure
```

Reinicie a API para carregar as URLs e o token novos; inicie o serviço e provisione os workflows:

```powershell
backend\.venv\Scripts\python.exe infrastructure\n8n-local.py start
backend\.venv\Scripts\python.exe infrastructure\conectar-n8n.py
```

O assistente cria o proprietário na instalação nova usando `DEMO_EMAIL` e a senha administrativa local, configura a credencial Header Auth e publica os seis workflows. Não redefine um proprietário existente. Os IDs ficam no manifesto privado `.runtime/n8n-workflows.json`; as credenciais são armazenadas pelo n8n com a chave de criptografia local. Nenhum segredo aparece nos exports ou no terminal.

O editor fica em `http://127.0.0.1:5678`. Após a configuração, **Iniciar NexoFiscal.cmd** inicia os três serviços: API, interface e n8n. O n8n escuta apenas no loopback, não possui agenda automática e não configura SMTP. As configurações SMTP existentes do NexoFiscal são preservadas.

Nesta instalação, entre no editor com `admin@nexofiscal.example.com` e a senha administrativa inicial do projeto. O usuário do n8n tem armazenamento próprio: alterações posteriores de senha no NexoFiscal não alteram a senha do editor. A primeira inicialização pode demorar enquanto carrega módulos e migra o banco; o iniciador aguarda o processo já registrado para evitar duplicação.

Os seis fluxos usam apenas Webhook e HTTP Request. O runner Python opcional não está instalado; seu aviso de inicialização não impede estes fluxos. Esta instalação é destinada à demonstração local. Docker/PostgreSQL e nodes de código Python exigem homologação própria.

Os workflows não retêm o conteúdo de execuções no n8n, para evitar armazenar cabeçalhos de autenticação e dados dos clientes. Consulte os resultados em **NexoFiscal → Automações → Histórico**; o contador de execuções retidas do editor pode ficar em zero.

Em **Automações → Executar**, escolha **n8n conectado** para passar pelo webhook real ou **API local** para executar diretamente. O histórico identifica a origem. O diagnóstico de conexão não substitui a confirmação de execução: `infrastructure/n8n-integration-check.py` verifica os seis fluxos reais e confere que documentos, clientes, financeiro e entregas de e-mail não aumentaram. O teste de pagamento reutiliza uma nota simulada já emitida.

Fontes de instalação: [n8n com npm](https://docs.n8n.io/hosting/installation/npm/) e [distribuição oficial do Node](https://nodejs.org/en/download).

As seis rotinas possuem implementação no backend e também podem ser executadas pela interface sem instalar n8n. A instalação de dependências não muda os estados de ativação. A execução explícita de `conectar-n8n.py` publica e habilita as seis rotinas, sem criar agendamentos.

## Usar no sistema

1. Entre como Administrador ou Financeiro e abra **Administração → Automações**. A conta pública Portfólio também pode operar a demonstração local; não ganha permissão de envio real de e-mail.
2. Na aba **Rotinas**, clique em **Ativar** e depois em **Executar**.
3. Escolha os parâmetros e confirme **Executar agora**.
4. Consulte o resultado, baixe o JSON ou reabra pela aba **Histórico**. O histórico mostra a origem Local ou n8n.

| Rotina / chave | Entrada | Resultado |
|---|---|---|
| Pagamento / `payment-confirmed` | `charge_id`: cobrança integralmente paga | Documento simulado com proteção contra duplicidade; link para a nota |
| Entrega / `document-delivery` | `invoice_id`: nota autorizada com PDF | Conferência do PDF e preparação da mensagem `.eml`; nenhum envio SMTP |
| Vencimentos / `due-reminders` | `days`: 1 a 90, padrão 7 | Cobranças vencidas e próximas, com textos para revisão; até 100 itens exibidos |
| Falhas / `failure-recovery` | `{}` | Rejeições e última entrega de cada nota quando falhou ou é desconhecida; até 100 ocorrências exibidas |
| Fechamento / `monthly-closing` | `competence`: `AAAA-MM`, mês atual por padrão | Previsto na competência, recebido no mês, saldo e contagens fiscais |
| Alertas / `alerts` | `{}` | Pendências financeiras, fiscais e de configuração, para consulta interna |

Lembretes e entrega preparam dados. Não enviam e-mails, não notificam terceiros e não reprocessam falhas automaticamente. O envio de documentos permanece na janela de e-mail da nota, restrito aos perfis já autorizados. Pagamentos continuam manuais/simulados; notas continuam sem validade fiscal.

## Conectar uma instalação n8n

1. Execute o Compose preparado no projeto ou use sua instalação n8n. No Compose, o editor está em `http://localhost:5678`; o proprietário é criado pelo assistente do n8n.
2. Configure `AUTOMATION_TOKEN` com ao menos 32 caracteres aleatórios, `N8N_HEALTH_URL` e `N8N_WEBHOOK_URL` no `.env`, sem colocar o segredo em arquivos de workflow. Reinicie a API. Para o fluxo de pagamento, mantenha o caminho `/webhook/fitnota-payment`, preservado por compatibilidade.
3. Na aba **Conexão n8n**, escolha onde o n8n será executado. O download ajusta a URL interna da API para `http://127.0.0.1:8010` (mesmo computador) ou `http://backend:8000` (Compose). Em outra topologia, ajuste o node HTTP para a URL acessível à sua instalação.
4. Baixe o workflow JSON e importe no editor. Os arquivos versionados em `n8n/workflows/` usam a topologia Docker.
5. Crie uma credencial **Header Auth** chamada **NexoFiscal Internal Token**. O cabeçalho é `X-Automation-Token`; seu valor é o token configurado no backend. Selecione a credencial no Webhook e no HTTP Request. O JSON contém apenas um nome genérico, sem segredos.
6. Ative a rotina no NexoFiscal e publique o workflow no n8n. São controles distintos.
7. Envie um POST autenticado ao webhook com os campos da tabela. O node HTTP chama `/api/automation/run/{chave}` e registra o resultado no histórico. Para pagamento, a ação **Encaminhar evento ao n8n** em Cobranças mantém a integração existente.

Os demais caminhos são `/webhook/nexofiscal-{chave}`. Os arquivos têm gatilho Webhook e ação HTTP, sem agenda automática. Um agendamento pode ser configurado depois, respeitando as autorizações de negócio. As rotinas exigem o ambiente fiscal de demonstração; nenhum arquivo transmite à prefeitura.

Os arquivos importados ficam **inativos** até a publicação deliberada no editor. Não é necessário compartilhar tokens no chat. A aba Conexão mostra apenas indicadores de configuração; não retorna os valores secretos. “n8n respondendo” verifica o healthcheck, sem provar que um workflow foi publicado.

Documentação oficial: [importação/exportação](https://docs.n8n.io/workflows/export-import/) e [HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/).

## Verificação

`backend/tests/test_automations.py` cobre ativação, seis rotinas, idempotência, isolamento, permissões, token interno, exportação sem segredos e ausência de SMTP. `infrastructure/automations-preview-server.py` e `automations-smoke.cjs` verificam a interface com banco temporário e dados fictícios; nunca use essas credenciais de QA no ambiente real.

Em 17/10/2026, `n8n-integration-check.py` confirmou os seis workflows publicados no serviço local, incluindo repetição idempotente, sem novas notas, pagamentos, cobranças, clientes ou entregas de e-mail. Evidência: `artifacts/n8n-integration.json`. `n8n-browser-check.cjs` confirmou conexão, seleção do n8n na execução de Alertas e resultado no histórico. As capturas ficam em `artifacts/screenshots/n8n`.
