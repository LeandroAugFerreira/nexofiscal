# Verificação de Gmail — 13/10/2026

Nenhum e-mail foi enviado. Nenhuma senha, token, cookie de sessão ou resposta detalhada de autenticação foi registrada. O arquivo `.env` e os fluxos existentes de emissão não foram alterados.

## Resultado

| Verificação | Resultado |
|---|---|
| Carregamento da configuração local | API lê `../.env` a partir de `backend`; sem arquivo `backend/.env` concorrente nem variáveis SMTP sobrescrevendo os campos verificados |
| Credencial SMTP | Presente; formato de senha de app conferido sem revelar seu conteúdo; validade ainda não confirmada |
| Remetente | `cliente.nfse.portifolio@gmail.com`, mantido conforme esclarecimento do usuário; login SMTP corresponde ao remetente |
| Host/porta gravados | `smtp.gmail.com:465`, TLS direto; preservados |
| Verificação separada em 587 | STARTTLS e TLS 1.3 negociados, certificado validado; conexão encerrada durante autenticação (`SMTPServerDisconnected`) |
| Comparação em 465 | TLS 1.3 e certificado válidos; mesmo encerramento durante autenticação |
| API | Estava parada. Iniciada em `127.0.0.1:8010`; healthcheck HTTP 200, configuração SMTP presente no endpoint da API |
| Interface | Iniciada na porta 5180; formulário de e-mail verificado em navegador isolado |
| Administrador/Financeiro | Logins HTTP 200, permissão `email_send` declarada pela API, botão Enviar e-mail habilitado na interface |
| Portfólio | Botão Enviar e-mail desabilitado; preparação de mensagem disponível |
| Módulo de e-mail | Rotas de preparação, envio e histórico presentes; seis testes aprovados com transporte SMTP simulado, incluindo STARTTLS antes de autenticar |
| Preparação | `.eml` com PDF fictício, assunto `[DEMONSTRAÇÃO]` e aviso `SEM VALIDADE FISCAL`; registros de entrega sem alteração |

O encerramento da conexão não retornou um código que confirme senha inválida. Portanto, não se afirma autenticação bem-sucedida nem se atribui a causa à senha. Falta distinguir restrição da rede/ambiente e problema de autenticação da conta.

### Diagnóstico posterior à primeira tentativa pela interface

A tentativa registrada pelo usuário está com situação `falhou`, antes do início da transmissão da mensagem. Nenhuma tentativa adicional de envio foi executada pelo agente.

Uma negociação sem credenciais recebeu `334` para `AUTH LOGIN` nas portas 465 e 587; foi cancelada imediatamente. O certificado pertence à Google Trust Services e a negociação TLS 1.3 permaneceu válida. Ao testar **LOGIN por desafio** com a configuração local na porta 465, o Gmail respondeu **535**, recusando a combinação de conta e senha de app. Esse resultado substitui a pendência genérica do diagnóstico inicial.

A camada de e-mail foi ajustada para usar LOGIN por desafio quando o Gmail anuncia esse mecanismo. Uma recusa de autenticação agora informa a necessidade de conferir a conta e atualizar a senha de app, sem expor a resposta técnica ou segredos. A configuração SMTP, a idempotência, as permissões e os fluxos de emissão de NFS-e foram preservados. Oito testes do módulo de e-mail passaram com SMTP simulado, incluindo sucesso e recusa do LOGIN por desafio sem envio no caso de recusa.

Correção pendente do usuário: na página [Senhas de app](https://myaccount.google.com/apppasswords), confira no avatar que a conta selecionada é **cliente.nfse.portifolio@gmail.com**, gere uma nova senha de app para NexoFiscal e grave-a usando `infrastructure/configurar-gmail.ps1`, na entrada oculta. A senha de app precisa pertencer à conta remetente; o diagnóstico não identifica se a senha anterior foi digitada incorretamente, revogada ou gerada em outra conta.

### Após a atualização da senha pelo usuário

A autenticação passou nas duas portas: **465 com TLS direto** e **587 com STARTTLS**, ambas negociando TLS 1.3 com certificado validado. O mecanismo LOGIN por desafio autenticou e o servidor respondeu `250` ao NOOP seguinte. Nenhuma mensagem foi enviada nesses testes, e a porta configurada permaneceu 465.

A API respondeu HTTP 200, carregou a configuração SMTP e o remetente esperado. Seu processo foi iniciado depois da atualização do `.env`, confirmando que houve reinicialização após a troca da credencial. O registro anterior de falha continua preservado como histórico; não foi reenviado nem convertido em sucesso.

O próximo envio real depende de uma ação explícita do usuário: atualizar a página da nota, abrir E-mail, conferir destinatário e PDF e clicar Enviar e-mail uma vez. O diagnóstico de autenticação, por si só, não autoriza nem dispara essa transmissão.

## Diagnóstico sem enviar mensagem

O comando abaixo usa a configuração local, testa a porta 587 separadamente e não modifica o arquivo nem chama envio de e-mail:

```powershell
Set-Location C:\Projetos\fitnota
.\backend\.venv\Scripts\python.exe .\infrastructure\verify-gmail.py --connect --port 587
```

Execute também no seu próprio PowerShell para comparar o resultado com o ambiente de execução da verificação. Se persistir o encerramento, confira a verificação em duas etapas e a validade da senha de app **nessa conta**. Trocar a porta, isoladamente, não resolveu o problema observado. Uma nova senha pode ser gravada pelo assistente de entrada oculta quando necessário, sem expô-la na conversa.

A documentação do [Gmail sobre SMTP/TLS](https://developers.google.com/workspace/gmail/imap/imap-smtp) descreve as portas 465/587. A [ajuda de senhas de app do Google](https://support.google.com/accounts/answer/185833?hl=pt-br) descreve a exigência de verificação em duas etapas e a revogação da senha de app quando a senha principal é alterada.

## Primeiro teste pela interface

1. Acesse `http://127.0.0.1:5180` com Administrador ou Financeiro. A senha de login do NexoFiscal é a senha da conta do sistema; não é a senha de app SMTP. O perfil Portfólio não pode enviar.
2. Abra `http://127.0.0.1:5180/invoices/29`, a nota fictícia `SIM-2026-000029`, autorizada no simulador e com PDF.
3. Clique **E-mail**. Confira o remetente `cliente.nfse.portifolio@gmail.com` e mantenha esse mesmo endereço como destinatário para enviar a si próprio.
4. Confira o PDF anexado e o assunto `[DEMONSTRAÇÃO]`. **Preparar mensagem .eml** gera somente o arquivo e pode ser usado agora, sem envio.
5. Depois de resolver a autenticação e decidir realizar o envio real do e-mail de teste, clique **Enviar e-mail** uma única vez. Este é o momento que transmite o e-mail; o PDF continua sendo demonstrativo, sem transmissão fiscal governamental.
6. Confira o histórico. **Aceita pelo SMTP** informa aceitação pelo servidor, não garante chegada à caixa de entrada. Confira Entrada/Spam. Em falha ou resultado desconhecido, consulte Enviados antes de iniciar outra operação.

Mensagem já preparada: `output/email/nexofiscal-primeiro-teste.eml`. Evidências locais: `artifacts/primeiro-teste-email.json` e `artifacts/email-interface-ready.png`. Os scripts de verificação não enviam mensagens; o teste de navegador bloqueia o endpoint de envio antes da rede como proteção adicional.
