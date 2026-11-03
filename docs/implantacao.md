# Execução e operação

Use README para comandos PowerShell e scripts de instalação. Em Docker Compose, frontend Nginx usa proxy `/api` na mesma origem, backend conecta a PostgreSQL na rede interna e n8n possui volume separado. Não há porta pública de PostgreSQL. Serviços HTTP publicados vinculam somente localhost.

O `.env.example` não contém senhas. `setup-local.ps1` gera senha demo quando vazia. `setup-docker.ps1` configura segredos vazios com aleatoriedade criptográfica; o segredo PostgreSQL gerado é hexadecimal, seguro para composição da URL. Se definir manualmente senha com caracteres reservados em URLs, faça o escape apropriado no `DATABASE_URL` ou utilize senha gerada. `.env`, certificados, bancos, logs e dependências ficam fora do Git.

Seed e migrations são independentes. Ao iniciar backend local, aplique `alembic upgrade head` primeiro; Docker aplica migração antes do Uvicorn. O seed não sobrescreve dados. Faça backup consistente do banco antes de qualquer atualização/downgrade real. `docker compose down` preserva volumes. Não use `down -v` para manutenção comum.

Mudanças para produção não estão concluídas nem autorizadas: HTTPS, `COOKIE_SECURE=true`, origens restritas ao domínio validado, gestão/revogação de usuários, limitação distribuída de login, controle/rotação de tokens, proteção de backups e logs, monitoração, retenção de dados e revisão de segurança operacional. A v0.1 foi projetada para demo local, não publicação pública automática.

PostgreSQL/Compose: a configuração foi escrita, mas não executada neste host. O n8n local foi validado separadamente em 17/10 com seis workflows publicados; isso não homologa o container n8n do Compose. Testes SQLite e geração offline de SQL PostgreSQL não substituem validação do runtime PostgreSQL, migrações no servidor no servidor PostgreSQL. Documente essas verificações após instalar Docker Desktop. Não há Redis, Tauri ou executável nesta versão.
