# NexoFiscal — estudo de caso técnico verificável

## Contexto

Prestadores de serviço precisam revisar cadastro, serviço, valor, competência e histórico de tentativas antes de entregar documentos. NexoFiscal usa esse domínio para demonstrar fluxos de software **sem qualquer autorização fiscal oficial**.

**Público:** operadores de demonstração, financeiro, contabilidade, administração e visitantes de portfólio. Nenhum cliente pagante, emissão real ou processo tributário foi medido.

## Problema e requisitos de engenharia

- Validar campos de cliente PF/PJ, serviço ativo, valor monetário e competência.
- Restringir operações por função e organização.
- Evitar duplicação quando uma operação HTTP for repetida.
- Preservar histórico de tentativas, rejeição, reprocessamento e cancelamento.
- Gerar HTML, PDF e XML **demonstrativos** consistentes com o snapshot persistido.
- Oferecer email manual opcional com autorização específica, **não** executá-lo por padrão.
- Isolar o contrato de futuros conectores fiscais sem afirmar que estão prontos.

## Solução implementada

Frontend React/Vite, backend FastAPI/Pydantic, SQLAlchemy + Alembic, SQLite local configurado e adaptador `SimuladorFiscalAdapter`. O cenário de portfólio centraliza as operações em `/api/fiscal`, deixando claro o ambiente `demonstracao` e provedor `simulador`.

### Fluxo A — prévia, emissão e documentos

1. Cadastro sintético de empresa PJ com CNPJ válido de teste e serviço “Consultoria” de R$ 350,00.
2. `POST /api/fiscal/preview` valida ativo, competência, valor, escopo e ambiente.
3. `POST /api/fiscal/issue-direct` com `Idempotency-Key` grava `Invoice`, eventos e snapshot, sem criar `Charge` ou `Payment`.
4. Identificador possui prefixo `SIM-` e HTML inclui a marca **DOCUMENTO SIMULADO — SEM VALIDADE FISCAL**.
5. PDF começa com assinatura de formato PDF, XML e HTML são disponibilizados por rotas autenticadas; não são oficiais.
6. Repetir a chave com mesmos dados retorna a mesma solicitação. Reutilizar com valor alterado retorna HTTP 409.

Evidência: [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py).

### Fluxo B — rejeitar, reprocessar e cancelar

1. A emissão é criada com `simulate_rejection=true` e status interno `rejeitada`.
2. O mesmo `Idempotency-Key` não cria outra nota; chave com payload diferente é recusada.
3. `POST /api/invoices/{id}/retry` aceita somente rejeição e move a simulação para `autorizada`.
4. Nova tentativa de retry em nota autorizada retorna HTTP 409.
5. `POST /api/invoices/{id}/cancel` exige autorização, status autorizado e motivo; acrescenta eventos `cancelamento_solicitado` e `cancelada`.
6. Cancelar novamente retorna HTTP 409; histórico e documento simulado permanecem rastreáveis.

Evidência: [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py).

### Fluxo C — permissão e dados inválidos

Entrada sem valor válido ou competência inválida é recusada; chave de operação curta retorna HTTP 422. Perfil `recepcao` não executa prévia/emissão ou cancelamento; operações negadas não modificam uma solicitação existente. Esse é **controle do backend**, não apenas esconder botões.

## Arquitetura e decisões

| Escolha | Benefício |
| --- | --- |
| Camada fiscal separada por serviços/adapters | Substituição futura do provedor sem misturar UI e domínio |
| `Idempotency-Key` + hash do payload | Replay seguro do mesmo conteúdo e detecção de conflito |
| Escopo por organização + RBAC | Limita leitura/escrita conforme o perfil e organização |
| Eventos `FiscalEvent` | Demonstra auditoria e reconstrução da linha do tempo |
| Snapshot persistido | O documento não precisa reconstruir dados atuais mutáveis |
| Simulação com watermark | Evita confundir resultado do sistema com documento fiscal válido |
| SMTP/n8n opcionais | Não dependem de serviço externo para o fluxo principal |
| Tour HTML estático | Triagem acessível sem publicar backend inseguro |

## Limitações

- Adaptadores NFS-e nacional/municipal não transmitem; lançam `NotImplementedError`.
- Nenhum modelo fiscal, assinatura, autorização pública, tributo ou município foi homologado.
- O CI agora executa pytest, build e um smoke Chromium **aprovado** no [run #42533982058](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533982058) com login/central/emissão avulsa. PostgreSQL e fluxo completo de emissão por cliques continuam pendentes.
- A conta pública de portfólio precisa reduzir privilégios antes de qualquer deploy.
- Não foi executado SMTP/n8n real nem criado um novo instalador Windows.
- Não foram medidas emissões, faturamento, economia ou clientes reais.

## Como apresentar em entrevista

Mostrar [tour estático](https://leandroaugferreira.github.io/nexofiscal-demo.html) identificado como simulação; abrir [arquitetura](ARQUITETURA.md); localizar [fiscal.py](../../backend/app/services/fiscal.py), [simulator.py](../../backend/app/fiscal/adapters/simulator.py), [official.py](../../backend/app/fiscal/adapters/official.py), [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py) e o [CI](EVIDENCIAS.md). Explicar por que “autorizada” é um estado **interno simulado**.

[15 perguntas](ENTREVISTA_TECNICA.md) · [Roteiro](ROTEIRO_DEMO.md).
