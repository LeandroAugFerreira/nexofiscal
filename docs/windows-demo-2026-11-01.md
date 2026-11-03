# NexoFiscal 0.1.0 — demonstração Windows

Verificação de 01/11/2026.

O executável reúne a interface compilada, API, migrações e guia HTML. Cria uma instalação fictícia fora do projeto, preservando o banco e a configuração do desenvolvedor. SMTP e n8n iniciam sem configuração. Toda emissão mantém o escopo simulado e sem validade fiscal.

## Resultado

- Build React aprovado.
- 60 testes backend aprovados em uma cópia isolada dos testes e com banco temporário.
- Iniciador em fonte aprovado em uma pasta nova.
- EXE aprovado com `frozen=true`, sem Python ou Node no PATH e com variáveis herdadas de banco, SMTP e n8n inválidas, ignoradas pela configuração da distribuição.
- Autenticação com CSRF, conta de portfólio, emissão avulsa simulada, PDF, documento HTML, preparação de mensagem `.eml` e bloqueio do envio real pelo visitante verificados.
- Repetição do seed, integridade SQLite e inicialização da janela de controle aprovadas. Os processos do autoteste foram encerrados.
- Scanner do binário e do pacote fonte: 4.145 conteúdos examinados na rodada inicial, sem achados de configuração ou credenciais pessoais. O guia e os estilos incluídos no EXE foram comparados com a edição web.

SHA-256 do executável: `3f210e12d3b4f834b489d573031f49a1dfa1ca42f083bb529a5a8c637ef7b451`.

O arquivo não possui assinatura digital. A inicialização Tk e as verificações HTTP não substituem uma inspeção visual completa em navegador real. Não houve envio de e-mail externo ou execução de n8n nestes testes. A distribuição não representa liberação para emissão fiscal oficial ou operação com dados reais.
