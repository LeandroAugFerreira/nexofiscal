# Teste de navegador real — NexoFiscal

**Script:** [infrastructure/browser_smoke_recruiting.py](../../infrastructure/browser_smoke_recruiting.py), acionado por [.github/workflows/tests.yml](../../.github/workflows/tests.yml).

## Escopo exato

O job tenta:
1. Criar banco SQLite temporário fora de qualquer diretório operacional.
2. Gerar senhas temporárias aleatórias para o administrador do seed; não imprimi-las.
3. Desativar acesso público de portfólio, SMTP, n8n e tokens de automação.
4. Aplicar as migrações Alembic e preparar seed sintético.
5. Iniciar API FastAPI em \`127.0.0.1:8018\` e Vite em \`127.0.0.1:5188\`, usando proxy para a API no mesmo host.
6. Abrir Chromium, autenticar administrador fictício via formulário, consultar Central e \`/api/fiscal/overview\`, confirmar que provedor é \`simulador\` e abrir a tela de emissão avulsa.
7. Capturar telas apenas com dados do seed e encerrar processos.

**Não** conclui um pedido fiscal pelo navegador, não chama adaptadores oficiais, não envia e-mail, não conecta n8n nem acessa prefeitura. A emissão/validação/retry/cancelamento são testados separadamente em pytest usando dados sintéticos. A captura não deve conter senha.

## Status e precisão

O primeiro job [#42533767951](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533767951) apresentou falha ao localizar a Central após login; backend e build permaneceram aprovados. Isso não pode ser contado como browser aprovado. Foi preparada uma correção usando endereço de fixture válido e um diagnóstico restrito ao texto visível da tela. **Somente registrar aprovação de browser após o job corrigido estar verde**, sem extrapolar a cobertura.

## Reproduzir com isolamento

O script altera e cria somente dados no diretório temporário que controla. Em checkout limpo, sem \`.env\` ou credenciais externas:

~~~bash
python -m pip install -r backend/requirements.txt
python -m pip install playwright==1.56.0
python -m playwright install --with-deps chromium
npm --prefix frontend ci
python infrastructure/browser_smoke_recruiting.py
~~~

O runner tem Ubuntu 24.04, Python 3.13 e Node 22; localmente o navegador pode exigir dependências do sistema. **Não executar contra instância real, bancos existentes ou serviços publicados.**

## Diferenciar as três evidências

- **Tour estático:** https://leandroaugferreira.github.io/nexofiscal-demo.html — só JavaScript local, sem emissão.
- **API real em teste:** pytest com SQLite e FastAPI/SQLAlchemy — executa validações, transições e documentos demonstrativos.
- **Navegador real em CI:** após aprovação, demonstra login e navegação, não substitui prova fiscal oficial.

[Resultados](EVIDENCIAS.md) · [Roteiro](ROTEIRO_DEMO.md).
