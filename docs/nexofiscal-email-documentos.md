# NexoFiscal — identidade empresarial, documentos e Gmail

A marca atual é **NexoFiscal — Gestão e emissão de NFS-e**. A interface adotou azul corporativo, tema claro inicial, tipografia Inter, menu azul-marinho e superfícies sem brilho. As opções Dark e Contraste continuam disponíveis. A pasta e os volumes técnicos anteriores foram preservados para manter os dados locais.

## Documento de demonstração

Novas emissões geram HTML, PDF A4 e XML demonstrativo, com dados preservados no momento da geração. O modelo organiza identificador, emitente, tomador, serviço, valores, informações municipais/federais e observações em blocos, com marca-d’água diagonal **DEMONSTRAÇÃO** e indicação **SEM VALIDADE FISCAL**. Uma simulação cancelada também recebe marca de cancelamento.

Referência visual e de campos: [NT 008/2026, versão 1.02 — Anexo I do DANFSe](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc/nt-008-se-cgnfse-danfse-20260714-v1-02.pdf). É uma representação local inspirada nessa organização, não um DANFSe autorizado pelo governo. O QR contém apenas identificador textual de demonstração; não aponta à consulta oficial. Tributos, alíquotas e enquadramentos não configurados permanecem explicitamente não calculados/parametrizados. Não são inventados número fiscal, chave de acesso válida, certificado ou assinatura governamental.

PDF: `/api/invoices/{id}/pdf`; para download, acrescente `?download=true`. XML: `/api/invoices/{id}/xml`; utiliza namespace próprio `urn:nexofiscal:demonstracao:v1`, não um schema transmitível da DPS nacional.

As notas antigas receberam uma representação moderna sem sobrescrever o HTML original. Quando não havia snapshot histórico completo, os campos adicionais foram complementados pelos cadastros disponíveis e o documento informa essa condição. Identificador, nome extraído do documento original, descrição e valor foram preservados. Backup das representações anteriores está em `backend/backups`.

## Conta de e-mail

A conta **cliente.nfse.portifolio@gmail.com** foi criada pelo usuário. O sistema está preparado para utilizá-la como remetente via SMTP autenticado, com configuração local concluída. O usuário confirmou o recebimento do documento demonstrativo com PDF no Gmail. A distribuição de código não inclui essa configuração nem suas credenciais.

Para ativar:

1. Entre **nessa conta** do Gmail e configure a verificação em duas etapas.
2. Quando a opção estiver disponível, [gere uma senha de app para NexoFiscal](https://myaccount.google.com/apppasswords). O Google exige verificação em duas etapas e pode restringir essa opção em determinados tipos de conta. [Orientação oficial](https://support.google.com/accounts/answer/185833?hl=pt-BR).
3. Execute o script abaixo e informe a senha de app na entrada oculta. Não use a senha normal do Gmail.

```powershell
Set-Location C:\Projetos\fitnota
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\infrastructure\configurar-gmail.ps1
```

O script grava a configuração no `.env`, ignorado pelo Git. Se a API deste workspace estiver ativa na porta 8010, reinicia somente essa instância; senão, siga os comandos de inicialização do README.

4. Entre no NexoFiscal com **Administrador** ou **Financeiro**. E-mail administrativo de demonstração: `admin@nexofiscal.example.com`; senha inicial demonstrativa `Adm@2026`, alterável em Minha conta.
5. Abra uma nota simulada autorizada, clique **E-mail**, confira destinatário e anexo e selecione **Enviar e-mail**.

SMTP: `smtp.gmail.com`, porta 465 com TLS; a camada também suporta porta 587 com STARTTLS e validação de certificado. OAuth pode ser acrescentado depois; o Google recomenda a opção “Fazer login com o Google” quando ela está disponível. Nenhuma senha é exposta na interface ou nos logs.

## Mensagem e resultado

**Avançado → Baixar mensagem (.eml)** cria uma mensagem MIME com assunto e corpo identificando a demonstração e o PDF anexo. A mensagem pode ser aberta em um cliente compatível; no Gmail Web, o PDF também pode ser anexado manualmente. Essa preparação funciona antes de configurar SMTP.

O perfil público **Portfólio** pode preparar o arquivo, mas não enviar mensagens reais. Administrador e Financeiro têm a permissão de envio. Repetir a mesma chave de operação retorna o mesmo registro sem disparar novamente. Em falha com resultado desconhecido, consulte a caixa de enviados antes de repetir uma nova operação.

“Aceita pelo SMTP” significa que o servidor aceitou a mensagem; não confirma chegada à caixa de entrada, leitura ou ausência de filtragem de spam. O resultado fica em `entregas_email` e é consultado no detalhe da nota. O usuário confirmou um recebimento real no Gmail durante a demonstração. Os testes automatizados utilizam transporte simulado e não enviam mensagens.

## Homologação fiscal

Integração oficial não é impossível por se tratar de portfólio: a Plataforma Nacional oferece ambiente de produção restrita/homologação. Ela exige atender aos requisitos de autenticação, cadastro do contribuinte, município, schemas e regras aplicáveis. O [manual oficial de API](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/manual-contribuintes-emissor-publico-api-sistema-nacional-nfs-e-v1-2-out2025.pdf) descreve o contexto e os requisitos. O NexoFiscal desta entrega continua totalmente local e simulado, sem transmissão fiscal.
