export const money = value => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(value || 0));
export const date = value => {
  if (!value) return '—';
  const instant = value.length <= 10 ? new Date(value+'T12:00:00Z') : new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : value+'Z');
  return new Intl.DateTimeFormat('pt-BR', {timeZone:'America/Sao_Paulo'}).format(instant);
};
export const dateTime = value => value ? new Intl.DateTimeFormat('pt-BR', {timeZone:'America/Sao_Paulo',dateStyle:'short',timeStyle:'medium'}).format(new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : value+'Z')) : '—';
export const today = () => {
  const parts = new Intl.DateTimeFormat('en-US', {timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  return ['year','month','day'].map(type=>parts.find(p=>p.type===type).value).join('-');
};
export const labels = {pendentes:'Todas as pendentes',pf:'Pessoa física',pj:'Pessoa jurídica',ativo:'Ativo', inativo:'Inativo', pendente:'Pendente', paga:'Paga', parcialmente_paga:'Parcial', vencida:'Vencida', cancelada:'Cancelada', suspenso:'Suspenso', cancelado:'Cancelado', autorizada:'Autorizada · SIM', rejeitada:'Rejeitada · SIM', aguardando_emissao:'Aguardando emissão', processando:'Processando', registrado_manual:'Manual / simulado', pix:'PIX', credito:'Cartão de crédito', debito:'Cartão de débito', dinheiro:'Dinheiro', boleto:'Boleto', transferencia:'Transferência', demonstracao:'Demonstração', portfolio:'Portfólio', administrador:'Administrador', financeiro:'Financeiro', recepcao:'Recepção', contabilidade:'Contabilidade'};
export const label = value => labels[value] || value || '—';
