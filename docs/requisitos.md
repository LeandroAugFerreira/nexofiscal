# Escopo entregue e evolução — 18/10/2026

O NexoFiscal é um emissor simulado de NFS-e para prestadores de serviços de diferentes setores. O escopo funcional de portfólio está concluído; emissão, revisão e acompanhamento do documento são o objetivo principal. O financeiro permanece como apoio.

## Entregue

- Clientes PF/PJ, serviços e dados da empresa emissora.
- Emissão guiada individual avulsa ou por cobrança quitada, revisão e confirmação explícita.
- Validação de CPF/CNPJ numérico, valores e competência; snapshots e idempotência.
- PDF/HTML com marca-d’água e XML demonstrativo; histórico, rejeição, reprocessamento e cancelamento simulados.
- Preparação `.eml` com PDF e envio manual SMTP para Administrador e Financeiro, com histórico e tratamento de resultado desconhecido.
- Login/logout, sessões, CSRF, perfis, conta Portfólio, criação/edição/desativação de usuários e atualização de dados/senha em Minha conta.
- Seis rotinas pela API local ou workflows autenticados no n8n, com ativação, origem, idempotência e resultado persistido.
- Busca, filtros, CSV, temas, layout móvel e paginação independente de cinco itens. Títulos, abas e filtros ficam fora da rolagem do conteúdo.
- Planos, contratos com preço preservado, cobranças por competência, pagamentos manuais parciais, indicadores e auditoria.

## Fora desta entrega

Integração governamental e autorização fiscal real; cálculo de impostos e regras oficiais; lotes; recorrência/prorrata financeira; estornos e conciliação; gateways; multiempresa; importação/exportação Excel; relatórios contábeis oficiais; OAuth; filas e envio automático; backup automatizado; executável e instalador independentes.

As rotinas preparam entrega/lembretes para revisão, diagnosticam falhas, consolidam resultados e verificam alertas. Não representam disparo por agendamento nem enviam e-mails automaticamente.

O XML tem formato próprio, não destinado à transmissão oficial. Identificadores `SIM-AAAA-NNNNNN` são internos. Os documentos mantêm identificação de simulação. O cadastro de CNPJ aceita o formato numérico; suporte a outros formatos exige evolução e homologação próprias.

## Ambiente e apresentação

Execução validada no Windows com SQLite. Docker Compose/PostgreSQL têm configuração e migrações, sem homologação de runtime. n8n foi validado localmente com seis workflows em 17/10; sua instalação e credenciais não acompanham o código. A distribuição cria um novo banco fictício e inicia sem SMTP.

O histórico está em `verificacao.md`; menções antigas a academia, usuários somente de leitura e cinco rotinas pendentes são registros de etapas anteriores, superados por este escopo.
