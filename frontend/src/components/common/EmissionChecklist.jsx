import {CheckCircle2, Circle, ShieldCheck} from 'lucide-react';

export default function EmissionChecklist({mode, client, service, charge, form, preview, environment}) {
  const amount = mode === 'avulsa' ? form.amount : charge?.amount;
  const competence = mode === 'avulsa' ? form.competence : charge?.competence;
  const checked = Boolean(preview);
  const items = [
    ['Cliente e documento', mode === 'avulsa' ? Boolean(client?.status === 'ativo' && (client.cpf || client.cnpj)) : Boolean(charge)],
    ['Serviço selecionado', mode === 'avulsa' ? service?.status === 'ativo' : Boolean(charge?.plan_name)],
    ['Valor positivo e em centavos', /^\d+(\.\d{1,2})?$/.test(String(amount ?? '')) && Number(amount) > 0 && Number(amount) < 1e10],
    ['Competência preenchida', /^\d{4}-(0[1-9]|1[0-2])$/.test(competence || '')],
    ['Simulador disponível', environment === 'demonstracao'],
  ];
  const count = items.filter(([, pass]) => pass).length;
  return <details className={`card emission-checklist ${checked ? 'validated' : ''}`} aria-label="Conferência da emissão">
    <summary className="checklist-heading"><ShieldCheck size={20}/><div><h2>Conferência dos dados</h2><span>{checked ? 'Dados conferidos' : `${count} de ${items.length} itens preenchidos`}</span></div></summary>
    <ul>{items.map(([text, pass]) => <li key={text} className={pass ? 'passed' : ''}>{pass ? <CheckCircle2 size={16}/> : <Circle size={16}/>}<span>{text}</span></li>)}</ul>
    <p>{checked ? 'Dados conferidos para a simulação. A emissão verifica os cadastros novamente.' : 'Avance em “Revisar dados” para concluir a conferência.'}</p>
    {form.simulate_rejection && <div className="checklist-rejection">Este exemplo produzirá uma rejeição simulada para demonstrar o tratamento de erros.</div>}
  </details>;
}
