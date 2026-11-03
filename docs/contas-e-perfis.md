# Contas e perfis

O fluxo foi adaptado do projeto local `transcricao-audio-web`: o Administrador cadastra pessoas com nome, e-mail, senha, perfil e status; pode editar dados, redefinir a senha e desativar o acesso. O projeto de referência não foi modificado.

No NexoFiscal, o próprio e-mail identifica o usuário. Os perfis existentes continuam sendo Administrador, Financeiro, Recepção e Contabilidade. Não há cadastro público que conceda acesso aos dados da empresa. O administrador inicial continua sendo provisionado pelo procedimento local já existente.

## Criar uma conta

1. Entre como Administrador.
2. Abra **Administração → Usuários → Novo usuário**.
3. Informe nome, e-mail, perfil e uma senha de 8 a 128 caracteres. Repita a senha.
4. Mantenha o status **Ativa** e clique em **Salvar usuário**.
5. A pessoa já pode entrar com o e-mail e a senha cadastrados. O cadastro não envia mensagens por e-mail.

Na lista, o botão de edição permite alterar os dados, o perfil e o status. Para redefinir a senha, preencha **Nova senha (opcional)** e sua confirmação. Campos de senha vazios mantêm a senha existente. Para remover o acesso, use **Inativa**; o histórico de operações é preservado.

## Minha conta

Clique no nome ou avatar, no canto superior direito. A aba **Dados pessoais** permite atualizar nome e e-mail mediante confirmação da senha atual. Em **Segurança**, informe a senha atual, uma nova senha e sua confirmação.

Alterações pessoais renovam a sessão atual e encerram as outras sessões da mesma conta. Alterações de e-mail, senha, perfil ou status feitas pelo Administrador encerram as sessões da conta alterada. Alterar apenas o nome de outra pessoa mantém suas sessões.

## Proteções

- Somente o perfil real Administrador gerencia contas; Financeiro e demais perfis não podem promover usuários.
- A consulta de usuários continua limitada à empresa da sessão; as alterações também respeitam esse limite.
- O Administrador usa Minha conta para editar os próprios dados. Não pode desativar a própria conta nem mudar o próprio perfil.
- Deve existir pelo menos um Administrador ativo. No PostgreSQL, as alterações bloqueiam os registros dos administradores durante a transação.
- A conta pública Portfólio consulta usuários, mas não cria ou altera contas e não altera sua própria senha ou dados.
- Senhas são armazenadas com Argon2 e nunca são retornadas em respostas ou auditorias. Erros de validação não repetem os dados recebidos.
- E-mails são normalizados e duplicidades são rejeitadas. A senha preserva espaços e diferencia maiúsculas de minúsculas.
- Escritas autenticadas exigem o token CSRF da sessão; mudanças de senha e dados pessoais exigem a senha atual e limitam tentativas.

Não foram alterados os fluxos fiscais nem a configuração SMTP. Esta funcionalidade não envia e-mails e não oferece recuperação automática por link. Para recuperar uma conta de usuário, o Administrador redefine sua senha pela lista. A conta inicial mantém o procedimento de configuração local existente.

## Validação

`backend/tests/test_accounts.py` cobre criação, login, permissões, duplicidade, validação, CSRF, isolamento entre empresas, restrições da conta pública, edição, desativação, reativação e invalidação de sessões. Os testes usam banco isolado e dados fictícios.

Para repetir a verificação visual sem alterar contas reais, execute `infrastructure/accounts-preview-server.py` com o Python do ambiente backend. Ele cria um banco temporário novo em `.tmp`, desabilita SMTP/n8n e atende apenas em `127.0.0.1:8011`. Com o frontend em `5180`, execute `infrastructure/accounts-smoke.cjs` com Playwright disponível. O script direciona as chamadas ao servidor de QA e bloqueia escritas fora de autenticação e usuários. Encerre o servidor de QA após a verificação.
