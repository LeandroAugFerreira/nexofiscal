# Fluxos para testar

Para a jornada atual, siga `central-emissao.md`: cliente PF/PJ → serviço e valor → revisão → documento. Os fluxos financeiros originais abaixo continuam disponíveis no grupo **Financeiro de apoio**, e o cadastro de alunos foi generalizado para **Clientes**.

1. Execute migração e seed. Entre usando `DEMO_EMAIL` e `DEMO_ADMIN_PASSWORD` configurados (ou `DEMO_PASSWORD` como fallback do seed).
2. Alunos → Novo aluno. Use dados fictícios e um CPF com dígitos verificadores válidos. Editar persiste; Inativar mantém histórico. O seed já possui alunos para teste.
3. Planos/Serviços → cadastrar, editar ou inativar. Valores de contratos existentes não mudam após alteração do plano.
4. Contratos → Novo contrato. Selecione aluno/plano ativos. Deixe valor vazio para capturar o preço do plano. Dia de vencimento: 1–28. É possível suspender, reativar ou cancelar; cancelamento é definitivo nessa versão.
5. Cobranças → Nova cobrança. Selecione contrato, competência e vencimento dentro da vigência. Desconto/acréscimo são opcionais. Um contrato só tem uma cobrança por competência.
6. Cobranças → Registrar pagamento manual ou Pagamentos → Registrar pagamento. Use o saldo completo ou parcial. Registro com data futura e valor superior ao saldo é bloqueado. Não há confirmação bancária nem dinheiro real.
7. Cobranças pagas → Solicitar emissão simulada. Marque rejeição para testar erro. Notas fiscais → consultar histórico, reprocessar uma rejeição, abrir documento e cancelar com motivo (administrador). Pagamento parcial não é elegível. Operação repetida não cria outra nota.
8. Dashboard → acompanhe novos valores e gráficos. Relatórios → filtre/exporte CSV. Alunos → detalhes mostra abas de contratos, cobranças, pagamentos, notas e histórico derivado.
9. Automações → Rotinas → Ativar → Executar. Confira resultados na aba Histórico. Não é necessário n8n para a execução local; a aba Conexão n8n apresenta o diagnóstico e os seis workflows para importar. Para integrar uma instalação externa, siga `n8n/docs/README.md`. Consulte a nota após qualquer falha de comunicação e não repita e-mails automaticamente.
10. Troque Dark/Light/Fitness no cabeçalho; a escolha persiste ao atualizar a página. Use Ctrl+K para busca global.

Documentos cancelados continuam disponíveis como registro histórico; sua situação cancelada consta na página e nos eventos. Não apresente o HTML histórico de uma simulação cancelada como documento em vigor.
