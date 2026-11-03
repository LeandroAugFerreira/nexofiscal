# Organização das telas — 14/10/2026

A navegação mantém emissão, consulta e cadastros no primeiro nível. Configuração fiscal fica em Administração; o financeiro permanece como apoio. O rodapé do menu oferece **Sobre e demonstração**, acessível em `/system`.

Atualização de 17/10/2026: títulos, subtítulos, ações principais e abas das páginas ficam em uma faixa fixa, fora da área rolável. Somente o conteúdo abaixo das abas rola; o topo e o menu lateral permanecem acessíveis. Ao trocar de tela ou aba, o conteúdo volta ao início. As abas de janelas, como o envio por e-mail, continuam dentro da própria janela. O comportamento também se aplica ao celular, com quebra de linha nos títulos e ações.

Os filtros também ficam na faixa fixa, abaixo das abas: busca e status de clientes/serviços/planos/contratos/cobranças/pagamentos, filtros de notas da Central e do Histórico fiscal, busca/perfil/acesso de usuários, parâmetros de relatórios e resultado do histórico de automações. `PageFilters` posiciona os controles fora da rolagem, preservando os valores e eventos. Abas de indicadores não exibem os filtros de registros; navegar para uma tela sem filtros remove a faixa correspondente.

As barras de rolagem usam espessura fina e cores próprias para cada tema e para o menu lateral. Abas não têm rolagem vertical; tabelas largas mantêm a rolagem horizontal dentro da tabela. Em notebooks com altura de até 800 px, o cabeçalho usa espaçamentos menores, mantendo fontes e controles na escala natural. Não é aplicado `zoom` ou redução por `transform` à interface; para restaurar o zoom do navegador a 100%, use **Ctrl + 0**.

## Paginação por bloco — 17/10/2026

Listas, tabelas, históricos e coleções de cartões exibem até **5 itens por página**, com números de página e ações **Anterior/Próxima**. Cada bloco tem uma página independente; mudar a lista de cobranças da visão financeira não muda pagamentos ou notas. Os filtros retornam à primeira página e a última página pode conter menos de cinco itens. O menu lateral mantém sua rolagem original.

O padrão se aplica aos cadastros e financeiro, Central e histórico de notas, pontos de atenção, usuários, auditoria, rotinas, execuções e resultados de automações, relatórios, exemplos, busca global, histórico do cliente, eventos fiscais e histórico de envio por e-mail. Os gráficos de valores cadastrais exibem cinco categorias por página; gráficos agregados preservam a base completa, com legenda paginada quando necessário. Campos de formulário, indicadores e documentos não são cortados pela paginação. CSV e downloads conservam os dados completos previstos em seus filtros.

`Pagination.jsx` centraliza os controles e o tamanho fixo de cinco; a API usa o mesmo padrão em `PAGE_SIZE`. `PaginatedItems` filtra a página de coleções já carregadas. Cadastros/notas/auditoria e execuções usam páginas da API. `/automations` informa `runs_total` filtrado e `runs_count` geral e aceita `page`/`status`; a auditoria passa a retornar cinco eventos. A busca aceita `paginate=true&page=N`, preservando o formato anterior quando o parâmetro não é usado. Pontos de atenção não são truncados; os demais registros ficam disponíveis nas próximas páginas.

## Onde encontrar cada informação

| Tela | Conteúdo principal | Conteúdo separado |
|---|---|---|
| Central de emissão | Indicadores, lista de solicitações e pontos de atenção | Explicação da jornada, prontidão e informações técnicas ficam em Sobre e demonstração |
| Histórico fiscal | Lista, filtros, paginação e CSV em largura total | Indicadores gerais permanecem na Central |
| Nota fiscal | Documento e ações de PDF/e-mail | Abas Dados da nota e Histórico fiscal |
| Envio por e-mail | Destinatário, PDF anexo, remetente e assunto | Histórico em aba própria; arquivo .eml em Avançado |
| Clientes, serviços e financeiro | Aba Registros com busca, filtros e ações | Totais e gráficos na aba Indicadores |
| Usuários | Lista e filtros | Perfis e permissões e Indicadores em abas próprias |
| Configuração fiscal | Aba Fiscal com os parâmetros atuais | Aba E-mail com remetente e disponibilidade |
| Sobre e demonstração | Ambiente e disponibilidade dos recursos | Exemplos PF/PJ/rejeição e Informações técnicas |

Os exemplos abrem `/emitir?scenario=pf`, `pj` ou `rejeicao` e continuam exigindo revisão e confirmação explícita. Apenas exemplos disponíveis para os cadastros fictícios da empresa são apresentados como ações. Na emissão, a conferência pode ser expandida e as opções de rejeição ficam em Opções de demonstração.

Os avisos repetidos nas páginas foram substituídos por uma faixa compacta de demonstração. PDF, HTML, XML e assunto/corpo dos e-mails conservam as identificações de simulação e ausência de validade fiscal.

O histórico de e-mail continua integral; nenhuma tentativa foi apagada ou convertida em outro resultado. As credenciais SMTP, as permissões e os fluxos de emissão foram preservados. A janela de e-mail separa a área de rolagem das ações, mantendo o botão de envio acessível em telas pequenas.

## Verificação

O build é executado com `npm run build` em `frontend`. A verificação da interface usa `infrastructure/organization-smoke.cjs`, com Edge/Playwright em contexto isolado. O teste percorre as novas abas, os cadastros, a revisão, os exemplos, a navegação pelo teclado, temas e o layout móvel. As chamadas de emissão e envio são bloqueadas pelo próprio teste. O script `infrastructure/email-interface-check.cjs` verifica Administrador, Financeiro e Portfólio com o endpoint de envio bloqueado.

Capturas ficam em `artifacts/screenshots/organization`. A apresentação atual de portfólio foi refeita em 18/10 com capturas de uma cópia isolada; o vídeo antigo de 77 segundos permanece como registro histórico.

`infrastructure/page-header-scroll-check.cjs` verifica as posições dos títulos, subtítulos e abas antes/depois da rolagem real em 18 telas e no detalhe da nota, além de teclado, navegação, temas, diálogos e viewport móvel. Capturas dessa verificação ficam em `artifacts/screenshots/page-headers`. O teste bloqueia alterações de dados e envio de mensagens.

`infrastructure/scrollbars-check.cjs` verifica a escala padrão de 100%, a roda do mouse, as barras e a ausência de overflow horizontal da página/conteúdo/menu em 1366×768, 1280×720, 1920×1080, 1024×768 e 390×844. Relatório em `artifacts/scrollbars-check.json` e capturas em `artifacts/screenshots/scrollbars`. Build e ambas as verificações de navegador aprovados após a padronização das barras.

Após a paginação, **60 testes backend** passaram, incluindo continuidade, ausência de duplicações, filtros e isolamento entre empresas. Build Vite e `page-header-scroll-check.cjs` aprovados. `pagination-check.cjs` confirmou páginas 1/2/3/última, retorno dos filtros à primeira página, blocos independentes, históricos, busca, gráficos, pontos de atenção e celular. As listas curtas foram ampliadas somente em respostas de leitura fictícias no navegador; nenhuma conta, cobrança ou nota foi criada e nenhum e-mail foi enviado. Capturas em `artifacts/screenshots/pagination`.

Após fixar os filtros, build Vite e `fixed-filters-check.cjs` aprovados. O teste confere a posição antes/depois da rolagem em dez telas e no histórico de automações, a busca com/sem resultados, a troca de páginas e abas, a remoção de filtros ao navegar e o encaixe em 1366×768 e 390×844. Capturas inspecionadas em `artifacts/screenshots/fixed-filters`; nenhuma emissão ou mensagem enviada.
