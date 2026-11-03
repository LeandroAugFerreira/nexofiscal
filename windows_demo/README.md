# NexoFiscal 0.1.0 — Windows

Abra `NexoFiscal.exe`, aguarde a inicialização e escolha **Entrar no portfólio**. Não é necessário instalar Python, Node.js, Docker ou n8n para esta edição. Mantenha a janela do programa aberta enquanto utiliza a interface no navegador.

O aplicativo cria uma base própria em `%LOCALAPPDATA%\NexoFiscal\0.1-demo`, aplica as migrações e provisiona os dados fictícios. Configuração de desenvolvimento, banco, SMTP e conexões n8n do autor ficam fora da distribuição. Execuções seguintes preservam a instalação.

Conta pública: `portfolio@nexofiscal.example.com` / `NexoFiscalDemo@2026`. O perfil não envia e-mail real. A conta administrativa demonstrativa é `admin@nexofiscal.example.com` / `Adm@2026`, conforme o modo de demonstração do projeto. Não utilize essas contas com dados reais ou em produção.

O botão Manual abre um guia HTML incluído no pacote. Toda emissão é simulada, identificada e sem validade fiscal. SMTP e n8n iniciam sem configuração. Nenhuma mensagem externa é enviada automaticamente.

## Compilação e validação

Gere `frontend/dist`, prepare PyInstaller 6.22.3 em uma pasta de ferramentas separada e execute `python -m PyInstaller windows_demo/NexoFiscal.spec`, informando diretórios de trabalho e saída fora de ambientes operacionais.

A especificação contém uma lista explícita de recursos, com frontend, migrações, manual e ícone. Não utiliza bancos do desenvolvedor. Execute o binário com `--self-test --data-dir <pasta-nova-vazia>` para validar HTTP, autenticação, emissão simulada, PDF, preparação de e-mail sem envio, persistência e integridade SQLite em uma instalação isolada.
