# Validação da cópia fonte — 02/11/2026

Backend/checagens existentes: **60 aprovados**.

Frontend: build: aprovado.

Os testes Python usaram ambientes já instalados, com segredos de ambiente removidos e arquivos temporários confinados à pasta de trabalho. O processo principal bloqueou DNS/conexões externas; conexões de loopback e subprocessos existentes foram revisados. Não foram iniciados n8n, envio SMTP real, conexão pessoal de IA ou transmissão fiscal. As simulações e documentos produzidos pelos testes são fictícios e não acompanham o pacote fonte.

Os testes inicialmente executados no sandbox não concluíram a inicialização; a execução isolada com acesso local adequado resolveu esse bloqueio de ambiente. Duas execuções completas pararam no limite inicial de cinco minutos, sem serem contabilizadas como aprovação. Os resultados acima usam as execuções concluídas e o reteste explicitado.

Dependências Python não foram instaladas ou adicionadas. Os builds reutilizaram dependências locais copiadas; para Chronos, o frontend foi restaurado em diretório novo pelo mesmo lockfile, sem scripts de instalação. Nenhum manifest da aplicação foi alterado. Os avisos de depreciação do adaptador de TestClient e o aviso de tamanho de chunk no build Chronos não foram tratados como novas funcionalidades ou como testes reprovados; não houve troca de dependências para suprimi-los.

Não houve instalação completa do backend a partir de ambiente vazio, teste de produção, novo build de EXE ou implantação. Os comandos do README foram conferidos no código, incluindo o preenchimento local de campos secretos deixados vazios nos exemplos. Consulte as execuções remotas na página de Actions; este documento registra a validação local.

As evidências estruturadas nesta pasta registram resultados reais. Os originais e os arquivos de lógica da aplicação foram preservados; somente documentação, exemplos sem credenciais e configuração de CI diferem na cópia.


---

## Validação posterior — estudo de recrutamento (08/11/2026)

A revisão adicionou **três testes backend** em [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py), sem modificar as regras fiscais. [GitHub Actions #42533352657](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533352657) concluiu **63 testes pytest aprovados**, um warning e build do frontend aprovado.

Um novo teste de Chromium/Playwright em SQLite temporário, com seed fictício e senha gerada aleatoriamente, foi **aprovado no [run #42533982058](https://github.com/LeandroAugFerreira/nexofiscal/actions/runs/42533982058)**. Confirmou autenticação via React, Central e acesso à tela de emissão avulsa. O navegador **não emitiu documento**, não executou SMTP/n8n e não interagiu com prefeitura. Não houve deploy de backend, PostgreSQL nem novo instalador Windows.

A [simulação pública no portfólio](https://leandroaugferreira.github.io/nexofiscal-demo.html) usa apenas HTML/CSS/JavaScript estático, sem banco/API ou validade fiscal. [EVIDENCIAS.md](../recrutamento/EVIDENCIAS.md) distingue testes executados, histórico e pendências.
