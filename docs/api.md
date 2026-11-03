# API

O fluxo principal está descrito em `central-emissao.md`: `/clients` e `/company` são os nomes atuais; as rotas antigas permanecem compatíveis. A Central usa `/fiscal/overview`, `/fiscal/ready-charges`, `/fiscal/preview` e `/fiscal/issue-direct`. Emissão avulsa aceita `client_id`, `service_id`, `amount`, `competence`, `description` e `simulate_rejection`, com `Idempotency-Key` obrigatório na emissão. Clientes usam `person_type=pf` com CPF ou `person_type=pj` com CNPJ; não podem informar os dois documentos ao mesmo tempo.

Base local: `http://127.0.0.1:8010/api`. Swagger: `/docs`. OpenAPI: `/openapi.json`.

| Grupo | Endpoints |
|---|---|
| Sessão | POST `/auth/login`, GET `/auth/me`, POST `/auth/logout` |
| Cadastro | GET/POST `/{students,plans,services}`, GET/PUT/DELETE `/{recurso}/{id}` |
| Aluno | GET `/students/{id}/history` |
| Contratos | GET/POST `/contracts`, PATCH `/contracts/{id}` (status) |
| Cobranças | GET/POST `/charges`, GET `/charges/{id}/eligibility` |
| Pagamentos | GET/POST `/payments` |
| Simulador | GET/POST `/invoices`, GET `/invoices/{id}`, GET `/invoices/{id}/document`, POST `/invoices/{id}/{retry,cancel}` |
| Indicadores | GET `/dashboard`, `/insights/{recurso}`, `/search?q=` |
| Configuração | GET/PUT `/academy`, GET/PUT `/fiscal-config` |
| Administração | GET `/users`, GET `/audit?page=1` |
| Automação | GET `/automations`, PATCH `/automations/{id}`, POST `/automations/{id}/run`, GET `/automations/{id}/workflow?target=local\|docker`, POST `/automations/dispatch/{charge_id}` |
| n8n interno | GET `/automation/charges/{id}`, POST `/automation/issue/{id}`, POST `/automation/run/{chave}` |
| Relatórios | GET `/reports/{contracts,charges,payments,invoices}.csv` |

Listas: `q`, `status`, `page` (mínimo 1), `page_size` (1–100); financeiro aceita `student_id`. CSV aceita `start`, `end`, `status`, `student_id`, `plan_id`. Datas ISO `YYYY-MM-DD`; competência `YYYY-MM`. Valores monetários JSON em strings decimais, por exemplo `"119.90"`. Status e nomes de campos estão documentados no Swagger.

Sessão em cookie HttpOnly. Após login/`me`, envie o campo `csrf_token` em `X-CSRF-Token` em mutações. POST de pagamento/emissão exige `Idempotency-Key` de 8–100 caracteres; reutilize a chave ao repetir a mesma operação. Chave de pagamento com payload diferente recebe 409. Uma cobrança é vinculada no máximo a uma solicitação fiscal; para rejeição use `/retry`, para cancelada não é possível gerar outra nota nesta versão.

Rotas n8n exigem `X-Automation-Token` igual ao segredo de pelo menos 32 caracteres no backend; não aceitam token de navegador. O token só acessa as rotas internas `/automation/*` e não é entregue à UI. Consultas de elegibilidade não expõem CPF nem dados pessoais de cadastro. Execuções `/automations/{id}/run` usam sessão e CSRF, exigem permissão `automation`, rotina ativa e `Idempotency-Key`. As seis rotinas e seus parâmetros estão em `../n8n/docs/README.md`; resultados são persistidos em `execucoes_automacoes` e retornados no histórico com origem Local ou n8n. Nenhuma rotina nova usa SMTP.

Erros: 401 sessão/token inválido, 403 perfil/CSRF/origem não autorizados, 404 registro inexistente ou de outra academia, 409 duplicidade/conflito de estado, 422 validação/regra, 429 limite de login. Erros de banco não devolvem parâmetros SQL nem segredos.
