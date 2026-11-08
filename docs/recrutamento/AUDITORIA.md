# NexoFiscal — auditoria técnica para recrutamento

**Referência:** código original em \`main\`, commit \`da74b8114d322e1abeeec1533d6f50532b3c46c0\` (08/11/2026). **Escopo:** leitura de módulos-chave e execução de três novos testes de integração. Não é pentest, avaliação fiscal oficial nem homologação governamental.

## Avaliação profissional

NexoFiscal é **um simulador de processos de documentos de serviço**, não um emissor NFS-e homologado. Seu valor para vagas Python/Backend/Full Stack está em: validações Pydantic, controle de acesso por papel/organização, idempotência, transações SQLAlchemy, máquina de estados, documentos demonstrativos e rastreabilidade com eventos. A jornada é mais convincente em entrevistas se explicada por testes reproduzíveis do que por um botão “Emitir NFS-e”.

## Arquivos examinados

- API e regras: [fiscal_center.py](../../backend/app/api/routes/fiscal_center.py), [business.py](../../backend/app/api/routes/business.py), [documents_delivery.py](../../backend/app/api/routes/documents_delivery.py), [fiscal.py](../../backend/app/services/fiscal.py).
- Adaptadores: [simulator.py](../../backend/app/fiscal/adapters/simulator.py), [official.py](../../backend/app/fiscal/adapters/official.py), [base.py](../../backend/app/fiscal/adapters/base.py).
- Formatos: [documents.py](../../backend/app/fiscal/documents.py); dados [entities.py](../../backend/app/models/entities.py), esquemas [inputs.py](../../backend/app/schemas/inputs.py).
- Segurança: [auth.py](../../backend/app/security/auth.py), [portfolio.py](../../backend/app/security/portfolio.py), [config.py](../../backend/app/core/config.py).
- QA: [test_fiscal_center.py](../../backend/tests/test_fiscal_center.py), [test_documents_email.py](../../backend/tests/test_documents_email.py), [test_flows.py](../../backend/tests/test_flows.py), [test_portfolio.py](../../backend/tests/test_portfolio.py), novo [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py).
- Interface: [IssueInvoice.jsx](../../frontend/src/pages/IssueInvoice.jsx), [FiscalCenter.jsx](../../frontend/src/pages/FiscalCenter.jsx), [api.js](../../frontend/src/services/api.js).
- Documentação histórica: [central-emissao.md](../central-emissao.md), [fiscal.md](../fiscal.md), [docs/github/VALIDACAO.md](../github/VALIDACAO.md).

A inspeção não cobriu exaustivamente todas as dependências, a infraestrutura Docker/Windows, fluxos SMTP externos ou segurança de produção.

## Fluxos implementados, com limites

| Capacidade | Evidência | Limite |
| --- | --- | --- |
| Clientes PF/PJ e serviços ativos | Rotas, validação CPF/CNPJ, Pydantic e testes | Documentos dos testes são fictícios |
| Prévia e emissão avulsa | POST /api/fiscal/preview e /issue-direct | Processamento **local simulado** |
| Emissão vinculada a cobrança | POST /api/invoices, exige quitação integral | Sem gateway bancário ou nota real |
| Idempotência | Idempotency-Key e fingerprint de dados para avulsa | Garante replay de mesmo payload nos casos testados |
| Rejeição/reprocessamento | Eventos + retry de rejeição | Rejeição é induzida pelo simulador; não é retorno de prefeitura |
| Cancelamento | Status “autorizada” → solicitação → “cancelada” | Cancelamento interno, sem protocolo fiscal oficial |
| Documento HTML/PDF/XML | Snapshot persistido, avisos visuais e identificador SIM | Formatos **demonstrativos**; não há DANFSe oficial |
| SMTP opcional | Preparação .eml e rota de envio com permissão | Envio real exige configuração; **não acionado** nesta etapa |
| n8n opcional | Workflows versionados e rotas protegidas | Não acionado/homologado nesta etapa |
| Adapter nacional/municipal | [official.py](../../backend/app/fiscal/adapters/official.py) | **NotImplementedError** nas operações oficiais |

## Segurança: forças e riscos

**Observável:** senha Argon2, sessão aleatória persistida como hash, cookie HttpOnly/SameSite, CSRF exigido em mutações, autorização por papel, escopo de organização no repositório e bloqueio de envio SMTP para conta de portfólio. Os testes existentes cobrem parte desses controles; isso não equivale a pentest.

**Riscos prioritários a investigar antes de qualquer backend público:**
- A conta \`portfolio\` recebe praticamente todas as permissões do administrador, exceto \`email_send\`. Mesmo com dados fictícios, isso é **escopo de escrita amplo demais** para visitantes de demonstração. Avaliar política de menor privilégio, reset entre visitantes e segregação de tenant.
- [config.py](../../backend/app/core/config.py) inclui senha de portfólio demonstrativa de valor padrão, \`cookie_secure=False\` por padrão e banco SQLite local. Configurações são aceitáveis apenas em contexto local isolado com medidas complementares, **não** como defaults para público.
- \`GET /api/auth/portfolio\` pode devolver credenciais explícitas quando habilitado; não disponibilizar esse fluxo num ambiente de produção.
- Há rotinas de SMTP/n8n capazes de causar efeitos externos se configuradas; não ativá-las por conveniência de uma demo.
- Testes ainda não validam PostgreSQL, varredura de dependências, rate limit distribuído, isolamento real entre visitantes ou deployments HTTPS.

**Restrição absoluta:** não chamar PDF/XML simulado de NFS-e válida, não sugerir transmissão real, não alegar cálculos fiscais oficiais e não apresentar os adaptadores \`NotImplemented\` como integrações concluídas.

## Verificações realizadas

[CI #42533352657](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533352657): **63 testes backend aprovados**, um warning, e **build React/Vite aprovado** após incluir três testes. Todos os dados foram sintéticos, SMTP e n8n desativados. O CI não inclui Playwright real nesta execução.

## Recomendações para recrutadores

Dizer: “NexoFiscal é um protótipo Full Stack que simula o ciclo de documentos de serviço, implementando pré-validação, idempotência por chave, estados persistidos, eventos de auditoria, autorização e geração de documentos claramente marcados sem validade fiscal.” Mostrar teste e código, não números de clientes, emissões reais, prefeitura ou ROI.

[Estudo de caso](ESTUDO_DE_CASO.md) · [Arquitetura](ARQUITETURA.md) · [Evidências](EVIDENCIAS.md) · [Plano](PLANO_DE_MELHORIAS.md).
