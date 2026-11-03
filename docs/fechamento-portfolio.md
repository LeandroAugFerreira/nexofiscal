# Fechamento de portfólio — 18/10/2026

O escopo funcional de emissão simulada foi encerrado na v0.1.0. A publicação apresenta o projeto, as capturas atuais, vídeos narrados e o código para execução local; não publica a API de emissão na internet.

## Instalação limpa

O ZIP foi extraído em uma pasta nova, sem copiar banco, `.env`, dependências ou runtime do autor. `setup-local.ps1 -Portfolio` criou a configuração, instalou requirements e npm, aplicou migrações, criou dados fictícios e habilitou o acesso público demonstrativo.

A API e o Vite foram iniciados em portas isoladas 8012/5182. O SMTP permaneceu desabilitado. Resultado:

| Verificação | Resultado |
|---|---|
| Instalação Python/Node e seed | Aprovados |
| Build React/Vite | Aprovado |
| Migrações e `alembic check` | Aprovados |
| `pytest -q`, com requirements-dev | 60 aprovados; um aviso de depreciação do cliente de testes |
| Jornada no Edge | Aprovada: filtros/CSV, PF/PJ, revisão, PDF, rejeição/reprocessamento, histórico, mensagem, cinco itens e celular |
| Envio de e-mail durante os testes | Nenhum; transporte desabilitado e endpoint bloqueado na captura |

O primeiro ensaio identificou que a instalação das dependências de desenvolvimento faltava nas instruções de teste. O README foi corrigido. Seletores do roteiro de captura também foram atualizados para a interface final. A validação passou após essas correções.

Relatório resumido em `release-check.json`. Reprodutores: `infrastructure/package-source.py`, `infrastructure/release-check.py` e `infrastructure/portfolio-flow-smoke.cjs`. O verificador de release espera o ZIP extraído em `.tmp/portfolio-release-check/NexoFiscal` e Playwright/Edge disponíveis.

## Apresentação e distribuição

Capturas feitas na cópia isolada com dados fictícios. Vídeos de cerca de 20 e 95 segundos, com o mascote já usado no portfólio, narração contínua Antonio em PT-BR, legendas PT/EN e controles compartilhados. Títulos e legendas ficam fora da imagem. Não há reprodução automática.

O pacote utiliza lista de arquivos permitidos. Configuração local, bancos, backups, logs, dependências e runtime n8n não são distribuídos. `.env.example` contém apenas credenciais públicas de demonstração e campos de SMTP vazios.

## Limites preservados

Não há autorização fiscal oficial, lotes, integração bancária, envio automático, executável independente ou homologação de runtime Docker/PostgreSQL. A integração n8n local de seis workflows foi validada em 17/10; o visitante configura sua própria instalação, ou usa as rotinas locais. O envio manual SMTP foi demonstrado anteriormente e o usuário confirmou recebimento; a publicação não disparou mensagens.

A verificação estática `portfolio-publish-check.cjs` aprovou cartão, página própria, reprodução dos vídeos, legendas PT/EN, pausa entre players, busca no vídeo, tela cheia, links, downloads e layout em 1440×1000, 1366×768 e 390×844. As capturas foram inspecionadas antes da publicação.
