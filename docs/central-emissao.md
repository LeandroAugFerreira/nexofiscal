# NexoFiscal — emissor de NFS-e para prestadores de serviços

A página inicial agora é a **Central de emissão**. Notas, pendências, rejeições, configuração fiscal e histórico ocupam o primeiro nível de navegação. Cadastros de clientes e serviços apoiam a emissão; contratos, cobranças, pagamentos e a visão financeira permanecem disponíveis em um grupo recolhível.

O produto atende clientes brasileiros pessoa física (CPF) e pessoa jurídica (CNPJ numérico), independentemente do setor do prestador de serviços. A identidade do produto é NexoFiscal. NFS-e para serviços é o escopo; NF-e/NFC-e para mercadorias e integração oficial continuam pendentes.

## Jornada principal

1. Entre com sua conta ou com **Entrar no portfólio**.
2. Na Central, selecione **Emitir NFS-e**.
3. Escolha o cliente PF/PJ; cadastro rápido está disponível para perfis com permissão.
4. Escolha um serviço, informe valor, competência e descrição.
5. Revise os dados validados pelo backend. Opcionalmente marque rejeição simulada para exercitar o tratamento de erros.
6. Clique **Emitir NFS-e simulada** e acompanhe o resultado.
7. Abra o documento ou o histórico fiscal. Rejeições podem ser reprocessadas e simulações autorizadas podem ser canceladas com motivo, conforme o perfil.

Na emissão avulsa, não é necessário criar plano, contrato, cobrança ou pagamento. O sistema também não cria esses registros automaticamente. Essa é uma solicitação fiscal interna do simulador, não confirmação de pagamento nem transmissão fiscal real.

O modo **Cobrança quitada** preserva o fluxo anterior: exige cobrança totalmente paga, cliente ativo e ausência de solicitação fiscal prévia. O backend confere novamente no momento da emissão. Uma cobrança continua vinculada no máximo a uma solicitação.

## Persistência e compatibilidade

- Migração `20261012_fiscal_central`: acrescenta PF/PJ, CNPJ e nomes empresariais aos clientes, permite nota avulsa com serviço e mantém a origem de notas antigas como cobrança.
- Novas rotas de cadastro: `/api/clients` e `/api/company`. Rotas `/api/students` e `/api/academy` permanecem compatíveis; tabelas internas antigas também são preservadas.
- Rotas fiscais: GET `/api/fiscal/overview`, GET `/api/fiscal/ready-charges`, GET `/api/fiscal/scenarios`, POST `/api/fiscal/preview`, POST `/api/fiscal/issue-direct`.
- Emissão avulsa exige `Idempotency-Key`; repetição com os mesmos dados retorna a mesma nota, enquanto chave reutilizada com outros dados recebe 409.
- Histórico, documento, valor e descrição da nota persistem. Nenhum documento fiscal existente foi reescrito.
- Downgrade é bloqueado se houver notas avulsas ou clientes PJ que a versão anterior não possa representar. Não há apagamento automático desses registros.

Antes da migração local foi criado backup SQLite em `backend/backups`. As 17 notas e os 58 eventos existentes permaneceram intactos, e a verificação de chaves estrangeiras não apontou inconsistências. A preparação genérica acrescentou serviços de consultoria, suporte, treinamento e projetos e um cliente PJ fictício. Serviços de academia originais do seed foram inativados; cadastros e documentos históricos foram mantidos.

Em instalações novas, o seed já fornece uma empresa e serviços genéricos. Em cópias existentes:

```powershell
Set-Location C:\Projetos\fitnota\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.general_demo
```

Use `app.general_demo` somente no banco demonstrativo. A rotina acrescenta dados fictícios e ajusta apenas a empresa/serviços reconhecidos do seed original.

Testes reproduzíveis: `pytest -q` para regras, permissões e persistência; `infrastructure/fiscal-smoke.cjs` para o fluxo no navegador. Os mesmos requisitos de demonstração e limitações de PostgreSQL/n8n/integração oficial descritos no README continuam aplicáveis.
