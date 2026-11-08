# NexoFiscal — melhorias priorizadas para recrutadores

**Data:** 08/11/2026. **Objetivo:** tornar a evidência técnica verificável, sem inventar integração oficial ou liberar um serviço inseguro.

| Ordem | Melhoria | Impacto | Esforço | Risco | Aceite verificável |
| --- | --- | --- | --- | --- | --- |
| P0 | Três testes de fluxo fiscal simulado, idempotência e RBAC | Confiança técnica em Python | Baixo | Baixo | Pytest verde com 63 casos e logs do CI |
| P0 | Tour estático web, com prefixo e watermark de simulação | Acesso rápido de recrutadores | Médio | Baixo | Página responsiva, sem API, dados fictícios |
| P0 | Auditoria/arquitetura/roteiro/15 perguntas | Comunicação e entrevista | Baixo | Baixo | Documento com links para código, teste e limites |
| P0 | Smoke Chromium local isolado com SQLite e credenciais aleatórias | Prova de UI integrada | Médio | Médio | CI verde, login/central/rota de emissão; sem SMTP/n8n |
| P1 | Revisar a conta pública de portfólio: privilégios mínimos e separação das mutações | Segurança pública | Médio | **Alto** se omitido | Role restrita e teste negativo de cada mutação |
| P1 | Remover defaults de senha demonstrativa de qualquer cenário remoto; exigir HTTPS/cookie Secure | Segurança | Médio | Alto | Configuração de produção falha sem segredos fortes e HTTPS |
| P1 | Isolamento de organizações e concorrência de requisições com PostgreSQL efêmero | Persistência | Médio | Médio | Migrations e testes de escopo/idempotência em CI PostgreSQL |
| P1 | Playwright cobrindo emissão rejeitada/retry/cancelamento por cliques reais | Engenharia Full Stack | Médio | Médio | Capturas e logs reprodutíveis de ambiente descartável |
| P1 | Threat modeling, CSRF/CSP/headers, dependências e sanitização de entradas | Segurança | Médio | Médio | Relatório e testes de regressão sem afrouxar proteção |
| P2 | Observabilidade, filas de documento e reconciliação de timeout | Backend/integração | Alto | Alto | Falhas simuladas não duplicam ou perdem eventos |
| P2 | Auditoria do envio SMTP e dos workflows n8n em sandbox fechado | Automação segura | Alto | Alto | Nenhuma mensagem real, teste com transportes fake |
| P3 | Estudo técnico sobre provedor fiscal oficial após autorização específica | Domínio futuro | Muito alto | **Muito alto** | Fontes oficiais, requisitos atualizados, conformidade revisada e homologação separada |

## Caminho de demonstração recomendado

O tour estático em https://leandroaugferreira.github.io/nexofiscal-demo.html mostra: prévia → emissão fictícia → replay → rejeição/retry → cancelamento, sem backend, contas ou dado pessoal. Recrutadores podem acompanhar pelo celular, abrir o código e conferir testes.

**Não hospedar a aplicação original para visitantes neste estado.** `portfolio` herda permissões amplas, as credenciais demo podem ser expostas quando o modo é habilitado, e o cookie Secure precisa de configuração. Para uma eventual demo real, criar tenant efêmero, roles estritas, HTTPS, expurgo, rate limit, observabilidade segura, dados totalmente fictícios, provedores externos desligados e testes independentes de segurança. Nunca reutilizar banco, documentos ou contas pessoais.

## Não comprovado

Não existe integração nacional/municipal oficial, certificação, protocolo da prefeitura, economia, clientes ou emissões reais. As rotinas SMTP/n8n são opcionais e podem produzir efeitos externos; não foram acionadas. O código da simulação não calcula impostos oficiais.

## Evolução de portfólio

Primeiro, corrigir segurança e adicionar teste de navegador completo; depois, PostgreSQL e testes de integração por organização. O retorno para recrutadores tende a ser maior que acrescentar telas sem prova de funcionamento.

[Auditoria](AUDITORIA.md) · [Evidências](EVIDENCIAS.md) · [Roteiro](ROTEIRO_DEMO.md).

## Progresso comprovado — 08/11/2026

Três novos testes backend aprovados com a suíte de 63; tour estático adicionado ao portfólio, sem backend público; smoke Chromium **aprovado** no [run #42533982058](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533982058), cobrindo login, Central e tela de emissão. Teste completo de processamento por cliques e segurança da conta pública permanecem pendentes.
