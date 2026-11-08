# NexoFiscal — roteiro de demonstração de 3 minutos

**Premissa:** o site público é um tour **estático** de regras de simulação, não acesso ao backend real. Nenhum documento é transmitido a prefeitura, assinado ou autorizado oficialmente.

## 00:00–00:25 — Problema

Abra [página do NexoFiscal](https://leandroaugferreira.github.io/nexofiscal.html).

**Fala:** “O NexoFiscal é um protótipo Full Stack para organizar a revisão e o histórico de documentos de serviço. Eu deliberadamente mantive o processo em modo simulado para estudar controle de estado, idempotência e autorização sem criar notas fiscais reais.”

## 00:25–01:05 — Prévia e emissão fictícia

Abra [demonstração interativa](https://leandroaugferreira.github.io/nexofiscal-demo.html). Escolha PJ ou PF, cenário de autorização, clique em Prévia e Simular emissão. Observe \`SIM-DEMO-001\` e aviso “DOCUMENTO SIMULADO — SEM VALIDADE FISCAL”.

**Fala:** “No backend verdadeiro, cliente e serviço precisam estar ativos, o documento PF/PJ passa por validação, e valor e competência são conferidos antes de gravar Invoice. Esta página apenas representa o resultado.”

## 01:05–01:35 — Idempotência

Clique Reenviar mesma chave; o total de registros permanece um.

**Fala:** “A API usa Idempotency-Key e hash do payload. Repetir com dados idênticos devolve a mesma solicitação. Usar a chave com outro valor resulta em conflito.”

Abra [teste real](../../backend/tests/test_recruiting_case.py).

## 01:35–02:05 — Rejeição/reprocessamento

Reinicie, selecione Rejeição simulada, clique Prévia e Emissão e depois Reprocessar. Explique que o status \`autorizada\` agora é **interno**, não aprovação da prefeitura. Mostre Cancelar e os eventos históricos.

**Fala:** “Eu preservei histórico de tentativas e não permito reprocessar uma nota que já não esteja rejeitada. Cancelamento exige uma nota simulada autorizada.”

## 02:05–02:35 — Arquitetura

Abra [ARQUITETURA.md](ARQUITETURA.md) e [fiscal.py](../../backend/app/services/fiscal.py). Mostre [official.py](../../backend/app/fiscal/adapters/official.py).

**Fala:** “Separei domínio, API, persistência, adapter simulador e contratos futuros. A implementação oficial ainda lança NotImplementedError, evitando uma falsa impressão de integração concluída.”

## 02:35–03:00 — Evidências e limites

Abra [GitHub Actions](https://github.com/LeandroAugFerreira/nexofiscal/actions) e [EVIDENCIAS.md](EVIDENCIAS.md).

**Fala:** “O CI executou 63 testes Python e build da interface. A segurança de um deploy público, PostgreSQL e autorização fiscal ainda não foram homologados. Um visitante não precisa de backend online para entender o case.”

## Contingências

- Se o tour web não estiver disponível, mostre os testes e os exemplos de JSON no repositório.
- Não usar dados reais, CPF/CNPJ de clientes, SMTP, n8n ou credenciais de operação.
- Não chamar PDF/XML simulado de documento fiscal válido e não afirmar conformidade tributária.
- O tour web não usa a API; evite dizer “emiti uma nota no navegador”.
- Se questionado sobre a conta de portfólio, reconheça explicitamente o escopo amplo da role e a necessidade de reduzir permissões antes de hospedar o backend.

[Estudo de caso](ESTUDO_DE_CASO.md) · [15 perguntas](ENTREVISTA_TECNICA.md).
