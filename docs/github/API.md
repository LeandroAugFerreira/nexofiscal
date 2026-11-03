# Inventário estático de rotas

Rotas identificadas nos decoradores do código. Prefixos aplicados ao incluir roteadores podem ser acrescentados ao caminho mostrado. Autenticação, permissões e payloads devem ser conferidos no código/OpenAPI; a tabela não dispensa validação nem comprova implantação.

| Arquivo | Método | Caminho declarado | Função |
|---|---|---|---|
| `backend/app/api/routes/accounts.py` | POST | `` | `create_account` |
| `backend/app/api/routes/accounts.py` | PUT | `/{identity}` | `update_account` |
| `backend/app/api/routes/auth.py` | GET | `/me` | `me` |
| `backend/app/api/routes/auth.py` | GET | `/portfolio` | `portfolio_credentials` |
| `backend/app/api/routes/auth.py` | POST | `/login` | `login` |
| `backend/app/api/routes/auth.py` | POST | `/logout` | `logout` |
| `backend/app/api/routes/auth.py` | PUT | `/me` | `update_me` |
| `backend/app/api/routes/auth.py` | PUT | `/password` | `update_password` |
| `backend/app/api/routes/automations.py` | GET | `/automations/{identity}/workflow` | `workflow_file` |
| `backend/app/api/routes/automations.py` | POST | `/automation/run/{key}` | `run_from_n8n` |
| `backend/app/api/routes/automations.py` | POST | `/automations/{identity}/run` | `run_local` |
| `backend/app/api/routes/business.py` | GET | `/academy` | `academy_get` |
| `backend/app/api/routes/business.py` | GET | `/audit` | `audits` |
| `backend/app/api/routes/business.py` | GET | `/automation/charges/{identity}` | `automation_charge` |
| `backend/app/api/routes/business.py` | GET | `/automations` | `automations` |
| `backend/app/api/routes/business.py` | GET | `/charges/{identity}/eligibility` | `charge_eligibility` |
| `backend/app/api/routes/business.py` | GET | `/clients/{identity}/history` | `student_history` |
| `backend/app/api/routes/business.py` | GET | `/company` | `academy_get` |
| `backend/app/api/routes/business.py` | GET | `/dashboard` | `dashboard` |
| `backend/app/api/routes/business.py` | GET | `/fiscal-config` | `config_get` |
| `backend/app/api/routes/business.py` | GET | `/invoices/{identity}` | `invoice_detail` |
| `backend/app/api/routes/business.py` | GET | `/invoices/{identity}/document` | `invoice_document` |
| `backend/app/api/routes/business.py` | GET | `/reports/{resource}.csv` | `csv_report` |
| `backend/app/api/routes/business.py` | GET | `/students/{identity}/history` | `student_history` |
| `backend/app/api/routes/business.py` | GET | `/users` | `users` |
| `backend/app/api/routes/business.py` | PATCH | `/automations/{identity}` | `automation_toggle` |
| `backend/app/api/routes/business.py` | PATCH | `/contracts/{identity}` | `contract_update` |
| `backend/app/api/routes/business.py` | POST | `/automation/issue/{identity}` | `automation_issue` |
| `backend/app/api/routes/business.py` | POST | `/automations/dispatch/{charge_id}` | `automation_dispatch` |
| `backend/app/api/routes/business.py` | POST | `/charges` | `charge_create` |
| `backend/app/api/routes/business.py` | POST | `/contracts` | `contract_create` |
| `backend/app/api/routes/business.py` | POST | `/invoices` | `invoice_create` |
| `backend/app/api/routes/business.py` | POST | `/invoices/{identity}/cancel` | `invoice_cancel` |
| `backend/app/api/routes/business.py` | POST | `/invoices/{identity}/retry` | `invoice_retry` |
| `backend/app/api/routes/business.py` | POST | `/payments` | `payment_create` |
| `backend/app/api/routes/business.py` | PUT | `/academy` | `academy_edit` |
| `backend/app/api/routes/business.py` | PUT | `/company` | `academy_edit` |
| `backend/app/api/routes/business.py` | PUT | `/fiscal-config` | `config_edit` |
| `backend/app/api/routes/documents_delivery.py` | GET | `/email/configuration` | `email_configuration` |
| `backend/app/api/routes/documents_delivery.py` | GET | `/invoices/{identity}/email` | `history` |
| `backend/app/api/routes/documents_delivery.py` | GET | `/invoices/{identity}/pdf` | `pdf` |
| `backend/app/api/routes/documents_delivery.py` | GET | `/invoices/{identity}/xml` | `xml` |
| `backend/app/api/routes/documents_delivery.py` | POST | `/invoices/{identity}/email-draft` | `draft` |
| `backend/app/api/routes/documents_delivery.py` | POST | `/invoices/{identity}/email-send` | `send` |
| `backend/app/api/routes/fiscal_center.py` | GET | `/overview` | `overview` |
| `backend/app/api/routes/fiscal_center.py` | GET | `/ready-charges` | `ready_charges` |
| `backend/app/api/routes/fiscal_center.py` | GET | `/scenarios` | `scenarios` |
| `backend/app/api/routes/fiscal_center.py` | POST | `/issue-direct` | `emit_direct` |
| `backend/app/api/routes/fiscal_center.py` | POST | `/preview` | `preview` |
| `backend/app/api/routes/insights.py` | GET | `/insights/{resource}` | `insights` |
| `backend/app/api/routes/insights.py` | GET | `/search` | `search` |
| `backend/app/main.py` | GET | `/api/health` | `health` |
