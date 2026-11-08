# Evidências técnicas do NexoFiscal — 08/11/2026

**Repositório:** LeandroAugFerreira/nexofiscal. **Dados:** exclusivamente sintéticos de teste e demonstração. Sem transmissão à prefeitura, pagamento, cliente real, SMTP/n8n operacional ou documento com validade fiscal.

## Execução efetivamente aprovada

- [GitHub Actions #42533352657](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533352657), commit `0e70f8ba2cfb3d3294f32a5d6f819dfd00fdce89`: **63 testes pytest aprovados**, 1 warning, **build frontend aprovado**.
- O incremento desta revisão foi de **três testes integrados**, adicionados em [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py) sobre a suíte anterior de 60 casos.
- **Chromium Playwright aprovado** no [CI #42533982058](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533982058), commit `4cc917cb3b52f72e6db4265662ccd8e430d4b1ec`: login React, Central autenticada, provedor simulador e página de emissão aberta. Não emitiu documento pela UI.

## Três casos novos comprovados pelo backend

### 1. Prévia, emissão avulsa e documento fictício

Cliente PJ com CNPJ de teste, serviço Consultoria (R$ 350,00), competência 2026-11. A API valida o cenário, cria `Invoice` com prefixo `SIM-` e status interno `autorizada`, produz HTML com aviso de ausência de validade fiscal, PDF e XML demonstrativos, sem gerar `Charge` ou `Payment`. O teste confirma snapshot e somente uma nota no banco descartável.

### 2. Rejeição, replay, retry, cancelamento e histórico

Emissão avulsa com rejeição simulada, replay com mesma chave/payload retorna o mesmo ID, chave com valor diferente recebe 409. Reprocessamento gera status interno `autorizada`, retry novamente gera 409, cancelamento com motivo é registrado e repetição é recusada. Teste valida eventos `rejeitada`, `autorizada`, `cancelamento_solicitado`, `cancelada` e quantidade persistida.

### 3. Validação e acesso

Valor não positivo, competência inválida e `Idempotency-Key` curta retornam 422. Perfil `recepcao` não pode obter prévia fiscal, emitir ou cancelar: API retorna 403. Tentativas recusadas não alteram a nota existente.

**Limites:** esses testes não provam concorrência irrestrita, certificado, assinatura digital, homologação NFS-e ou envios externos. Há outros testes existentes para concorrência, autenticação, escopo, SMTP simulado e auditoria, cuja cobertura própria deve ser consultada antes de generalizar.

## Verificação com navegador

O job de Chromium foi **executado e aprovado**, com SQLite temporário, segredos aleatórios, migrations e seed sintético, FastAPI e Vite somente em `127.0.0.1`. Validou login, Central e tela de emissão; não executou emissão pela UI, e-mail ou n8n. [Execução verificável](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533982058).

## Demo pública estática

[Tour do NexoFiscal](https://leandroaugferreira.github.io/nexofiscal-demo.html) em HTML/CSS/JavaScript. É uma **visualização isolada**, não executa API, não persiste dados e não produz documento fiscal válido. O prefixo `SIM-DEMO-001` é um identificador da interface, não a saída numérica de um backend. Dados fixos fictícios.

## Verificações históricas

[docs/github/VALIDACAO.md](../github/VALIDACAO.md): 60 casos backend aprovados antes dos três testes novos. [docs/fechamento-portfolio.md](../fechamento-portfolio.md): histórico de execução local em Windows/Edge em outubro de 2026. Não contabilizar essas execuções como realizadas agora.

## Não homologado nesta etapa

- NFS-e nacional, municipal, prefeitura, certificados, XML oficial, cálculo de tributos ou cancelamento oficial.
- PostgreSQL runtime/migrações, pen test, produção HTTPS, segregação de visitantes ou retenção de documentos pessoais.
- Envio SMTP ou execução n8n real; automações podem ter efeitos externos e permaneceram sem configuração.
- Instalador Windows novo, execução completa da UI de emissão por cliques, testes de acessibilidade e desempenho.

[Auditoria](AUDITORIA.md) · [Arquitetura](ARQUITETURA.md) · [Plano priorizado](PLANO_DE_MELHORIAS.md).
