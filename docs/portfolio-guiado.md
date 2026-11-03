# Demonstração guiada — 18/10/2026

## Jornada principal

1. Execute a instalação e entre pela opção **Entrar no portfólio**.
2. Abra **Sobre e demonstração → Demonstração** e escolha o exemplo PF, PJ ou rejeição.
3. O exemplo preenche dados fictícios em **Emitir NFS-e**. Nenhuma nota é criada ao selecionar o exemplo.
4. Avance por cliente, serviço/valor e revisão. A conferência pode ser expandida; **Dados conferidos** indica a revisão pelo servidor.
5. Confirme **Emitir NFS-e simulada**, abra o documento e baixe o PDF.
6. No detalhe da nota, consulte as abas Documento, Dados da nota e Histórico fiscal. O exemplo de rejeição permite reprocessar e consultar as tentativas.
7. Em **E-mail**, o visitante pode preparar o arquivo em **Avançado → Baixar mensagem (.eml)**. O botão de envio real exige Administrador/Financeiro e um remetente próprio configurado.
8. Em **Automações**, consulte as seis rotinas. A instalação sem n8n permite execução pela API local; conectar n8n é opcional e exige instalação e credenciais próprias.

Listas e históricos têm cinco itens por página. Cada bloco mantém sua página; filtros voltam à primeira. Títulos, abas e filtros permanecem fixos enquanto o conteúdo rola.

A emissão avulsa não cria cobrança ou pagamento. Todas as representações mantêm marca-d’água e identificação de simulação. Não há emissão oficial ou transmissão governamental.

## Apresentação atual

A apresentação pública segue o padrão dos demais projetos do portfólio: capturas reais, mascote no canto inferior esquerdo, voz masculina contínua em português, títulos e legendas fora da imagem, player compartilhado, sem reprodução automática. A narração usa Antonio, ritmo +3% e tom -2Hz. Legendas PT-BR/inglês e títulos são sincronizados às palavras.

Arquivos locais:

- `output/video/nexofiscal-resumo.mp4`: cerca de 20 segundos.
- `output/video/nexofiscal-apresentacao.mp4`: cerca de 95 segundos.
- `output/video/*-pt.vtt` e `*-en.vtt`: legendas externas.
- `artifacts/portfolio-demo/`: capturas atuais de uma instalação isolada com dados fictícios.
- `docs/roteiro-portfolio.json`: textos e sequência da apresentação.

O vídeo silencioso anterior de 77 segundos é um registro histórico e não é usado na publicação atual.

## Reprodução e ferramentas opcionais

Com a aplicação ativa, Edge e Playwright disponíveis:

```powershell
node .\infrastructure\portfolio-flow-smoke.cjs
```

`FITNOTA_DEMO_URL` permite apontar para uma instalação de QA. O script cria duas solicitações fictícias, prepara uma mensagem, bloqueia o endpoint de envio, verifica filtros/CSV, revisão, rejeição/reprocessamento, PDF, paginação e celular. Não envia e-mail.

Para montar os vídeos, instale separadamente Pillow, NumPy e edge-tts, com FFmpeg no PATH, e execute `infrastructure/build-portfolio-video.py`. A captura e os vídeos não são necessários para executar o aplicativo. A criação de voz requer internet e transmite apenas os textos públicos do roteiro. O parâmetro `--mascot` informa o PNG do mascote existente no portfólio; o arquivo original é preservado.

A geração final utilizou edge-tts 7.3.1, revisão `bd44c1d1aaebdc1db7f47456ee12431b42ec7cac` do repositório oficial. A versão antiga 7.2.8 não conectou ao serviço e foi substituída somente na pasta isolada de ferramentas.

## E-mail

O usuário confirmou anteriormente o recebimento de uma mensagem com PDF no Gmail. Isso é distinto das verificações automatizadas de publicação: elas usam SMTP desabilitado e bloqueiam o endpoint de envio. A distribuição inicia sem conta remetente; configure uma conta própria para experimentar esse recurso.
