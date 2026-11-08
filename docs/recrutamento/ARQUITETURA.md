# NexoFiscal — arquitetura auditada

**Arquitetura do protótipo**, sem indicação de backend hospedado, integração fiscal oficial ou SMTP ativo.

~~~mermaid
flowchart LR
  P[Operador local / conta de teste] --> UI[React/Vite]
  UI --> HTTP[API /api FastAPI]
  HTTP --> AUTH[Cookie HttpOnly, CSRF, RBAC e organização]
  HTTP --> CENTER[Central fiscal: prévia e emissão]
  CENTER --> SERVICE[services/fiscal.py]
  SERVICE --> ADAPTER[SimuladorFiscalAdapter]
  SERVICE --> STORE[(SQLAlchemy / SQLite local)]
  ADAPTER --> SNAP[Snapshot persistido]
  SNAP --> DOC[HTML, PDF e XML demonstrativos]
  STORE --> EVENTS[FiscalEvent / Invoice]
  HTTP --> EMAIL[SMTP manual opcional]
  HTTP --> AUTO[n8n opcional]
  OFFICIAL[Adapters Nacional/Municipal] -.-> BLOCK[NotImplementedError / integração indisponível]
~~~

Os serviços SMTP/n8n não são requisitos do teste e podem ter efeitos externos se configurados; nenhum deles é necessário para gerar documento simulado.

## Emissão direta

~~~mermaid
sequenceDiagram
  autonumber
  actor U as Operador autorizado
  participant API as /api/fiscal
  participant S as services/fiscal
  participant DB as SQLAlchemy / DB
  participant A as SimuladorFiscalAdapter
  U->>API: POST /preview
  API->>S: Validar cliente, serviço, valor e ambiente
  S->>DB: Consultar cadastro no escopo da organização
  API-->>U: Prévia / verificações do simulador
  U->>API: POST /issue-direct + Idempotency-Key
  API->>S: Fingerprint do payload / replay
  alt Mesma chave e mesmo payload
    S-->>U: Solicitação existente
  else Chave em conflito
    S-->>U: HTTP 409
  else Nova solicitação válida
    S->>DB: Criar Invoice / evento
    S->>A: Processar simulação
    A->>DB: Snapshot + HTML/PDF/XML simulados
    S->>DB: Gravar status, eventos e auditoria
    API-->>U: Resultado interno simulado
  end
~~~

## Rejeição e cancelamento

~~~mermaid
stateDiagram-v2
  [*] --> aguardando_emissao
  aguardando_emissao --> processando
  processando --> autorizada: simulador aceita
  processando --> rejeitada: rejeição induzida
  rejeitada --> processando: retry autorizado
  autorizada --> cancelamento_solicitado: cancelamento autorizado
  cancelamento_solicitado --> cancelada: simulador conclui
~~~

**Importante:** todos os estados são da própria aplicação. \`autorizada\` não significa aprovação por prefeitura nem geração de NFS-e válida.

## Persistência

Entidades reais em [entities.py](../../backend/app/models/entities.py): \`Invoice\`, \`FiscalEvent\`, \`FiscalConfig\`, \`Student\` (cliente legado), \`Service\`, \`AuthSession\`, \`Charge\`, \`Payment\`, \`EmailDelivery\`, \`Audit\`. Uso de Alembic para mudanças de schema; SQLite nos testes atuais, PostgreSQL/Compose declarados, não homologados no CI desta revisão.

## Separação de responsabilidades

- [API](../../backend/app/api/routes/fiscal_center.py) — endpoints de prévia, emissão e cenários.
- [Serviço](../../backend/app/services/fiscal.py) — regras de elegibilidade, idempotência, estados e eventos.
- [Simulador](../../backend/app/fiscal/adapters/simulator.py) — identificador \`SIM-\` e geração demonstrativa.
- [Adaptadores oficiais](../../backend/app/fiscal/adapters/official.py) — contratos **não implementados**.
- [Documentos](../../backend/app/fiscal/documents.py) — snapshots, HTML/PDF/XML com avisos.
- [Segurança](../../backend/app/security/auth.py) — sessão, CSRF, perfis.
- [Frontend](../../frontend/src/pages/IssueInvoice.jsx) — jornada do operador.
- [Testes](../../backend/tests/test_recruiting_case.py) — comprovação de regras no backend.

[Auditoria](AUDITORIA.md) · [Estudo de caso](ESTUDO_DE_CASO.md).
