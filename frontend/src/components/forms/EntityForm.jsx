import {useEffect,useState} from 'react';
import {LoaderCircle} from 'lucide-react';
import {all,write,api} from '../../services/api';
import {label,money,today} from '../../utils/format';
import {useUI} from '../../contexts/UIContext';
import {Loading,ErrorState} from '../common/Primitives';

const addressFields=[['cep','CEP'],['street','Logradouro'],['number','Número'],['complement','Complemento'],['neighborhood','Bairro'],['city','Município'],['state','UF']].map(([key,title])=>({key:`address.${key}`,title,maxLength:key==='state'?2:160}));
const statusField={key:'status',title:'Status',type:'select',options:['ativo','inativo']};
const price={key:'price',title:'Valor (R$)',type:'number',step:'.01',min:0,required:true};
export const definitions={
  students:{title:'cliente',permission:'students',fields:[{key:'person_type',title:'Tipo de pessoa',type:'select',options:['pf','pj'],required:true},{key:'name',title:'Nome completo / razão social',required:true,minLength:3},{key:'cpf',title:'CPF',required:true,condition:'pf'},{key:'cnpj',title:'CNPJ',required:true,condition:'pj'},{key:'trade_name',title:'Nome fantasia',condition:'pj'},{key:'municipal_registration',title:'Inscrição municipal',condition:'pj'},{key:'birth_date',title:'Nascimento',type:'date',condition:'pf'},{key:'email',title:'E-mail',type:'email'},{key:'phone',title:'Telefone'},...addressFields,statusField,{key:'notes',title:'Observações internas',type:'textarea'}]},
  plans:{title:'plano',permission:'catalog',fields:[{key:'name',title:'Nome do plano',required:true,minLength:3},price,{key:'period_months',title:'Periodicidade (meses)',type:'number',min:1,max:36,required:true},{key:'description',title:'Descrição',type:'textarea'},{key:'services',title:'Serviços incluídos',type:'textarea'},statusField]},
  services:{title:'serviço',permission:'catalog',fields:[{key:'name',title:'Nome do serviço',required:true,minLength:3},price,{key:'unit',title:'Unidade',required:true},{key:'description',title:'Descrição',type:'textarea'},{key:'fiscal_reference',title:'Referência fiscal (sem parametrização oficial)'},statusField]},
  contracts:{title:'contrato',permission:'finance',fields:[{key:'student_id',title:'Cliente',type:'relation',source:'clients',required:true},{key:'plan_id',title:'Plano',type:'relation',source:'plans',required:true},{key:'amount',title:'Valor contratado (R$)',type:'number',step:'.01',min:0,help:'Vazio: usa o valor atual do plano. Preservado após a contratação.'},{key:'start_date',title:'Início',type:'date',required:true},{key:'end_date',title:'Término',type:'date'},{key:'due_day',title:'Dia do vencimento',type:'number',min:1,max:28,required:true}]},
  charges:{title:'cobrança',permission:'finance',fields:[{key:'contract_id',title:'Contrato',type:'relation',source:'contracts',required:true},{key:'competence',title:'Competência',type:'month',required:true},{key:'due_date',title:'Vencimento',type:'date',required:true},{key:'discount',title:'Desconto (R$)',type:'number',step:'.01',min:0},{key:'surcharge',title:'Acréscimo (R$)',type:'number',step:'.01',min:0}]},
  payments:{title:'pagamento manual',permission:'finance',fields:[{key:'charge_id',title:'Cobrança em aberto',type:'relation',source:'charges',required:true},{key:'amount',title:'Valor pago (R$)',type:'number',min:'.01',step:'.01',required:true},{key:'paid_at',title:'Data do pagamento',type:'date',required:true},{key:'method',title:'Forma de pagamento',type:'select',options:['pix','dinheiro','credito','debito','boleto','transferencia'],required:true},{key:'reference',title:'Referência / comprovante interno'}]},
  invoices:{title:'emissão simulada',permission:'fiscal',fields:[{key:'charge_id',title:'Cobrança paga',type:'relation',source:'charges',required:true},{key:'simulate_rejection',title:'Simular rejeição para testar o tratamento de erro',type:'checkbox'}]},
  academy:{title:'empresa',permission:'settings',fields:[{key:'legal_name',title:'Razão social',required:true},{key:'name',title:'Nome fantasia',required:true},{key:'cnpj',title:'CNPJ',required:true},{key:'municipal_registration',title:'Inscrição municipal'},{key:'email',title:'E-mail',type:'email'},{key:'phone',title:'Telefone'},...addressFields,{key:'tax_regime',title:'Regime tributário (referência cadastral)'}]},
  'fiscal-config':{title:'configuração fiscal',permission:'settings',fields:[{key:'environment',title:'Ambiente',type:'select',options:['demonstracao']},{key:'provider',title:'Provedor',type:'select',options:['simulador']},{key:'municipality',title:'Município'}]},
};
definitions.clients=definitions.students;
definitions.company=definitions.academy;
const defaults={person_type:'pf',status:'ativo',period_months:1,unit:'sessão',fiscal_reference:'Não configurada',start_date:today(),due_date:today(),paid_at:today(),competence:today().slice(0,7),due_day:10,discount:'0',surcharge:'0',method:'pix',environment:'demonstracao',provider:'simulador'};
export function EntityForm({resource,record,onSaved,onCancel}) {
  const def=definitions[resource],{notify}=useUI();
  const [values,setValues]=useState({...defaults,...record}),[relations,setRelations]=useState({}),[loading,setLoading]=useState(true),[error,setError]=useState(''),[saving,setSaving]=useState(false);
  const fields=def.fields.filter(field=>!field.condition||field.condition===values.person_type);
  const [key]=useState(()=>crypto.randomUUID());
  useEffect(()=>{
    let alive=true;
    const sources=[...new Set(def.fields.filter(x=>x.source).map(x=>x.source))];
    Promise.all(sources.map(async source=>[source,await all(source)])).then(results=>{if(alive){setRelations(Object.fromEntries(results));setLoading(false);}}).catch(e=>{if(alive){setError(e.message);setLoading(false);}});
    return()=>{alive=false;};
  },[resource]);
  const get=field=>field.key.startsWith('address.')?values.address?.[field.key.split('.')[1]]||'':values[field.key]??'';
  function change(field,value){if(field.key==='person_type'){setValues(previous=>({...previous,person_type:value,cpf:'',cnpj:'',birth_date:null,trade_name:'',municipal_registration:''}));return;}setValues(previous=>field.key.startsWith('address.')?{...previous,address:{...previous.address,[field.key.split('.')[1]]:value}}:{...previous,[field.key]:value});}
  function options(field){
    const list=relations[field.source]||[];
    return list.filter(row=>{
      if(field.source==='charges')return resource==='invoices'?row.status==='paga':Number(row.balance)>0&&row.status!=='cancelada';
      return row.status==='ativo';
    }).map(row=>({value:row.id,title:field.source==='charges'?`#${row.code} · ${row.student_name} · ${row.competence} · ${money(resource==='payments'?row.balance:row.amount)}`:field.source==='contracts'?`#${row.code} · ${row.student_name} · ${row.plan_name}`:`${row.name}${row.price?' · '+money(row.price):''}`}));
  }
  async function submit(e){
    e.preventDefault();setSaving(true);setError('');
    const payload={};
    for(const field of fields){
      let value=get(field);
      if(field.key.startsWith('address.')){payload.address={...payload.address,[field.key.split('.')[1]]:value};continue;}
      if(field.type==='checkbox')value=!!value;
      if(field.type==='relation'||['period_months','due_day'].includes(field.key))value=Number(value);
      if(['birth_date','end_date','amount'].includes(field.key)&&value==='')value=null;
      if(['discount','surcharge'].includes(field.key)&&value==='')value='0';
      payload[field.key]=value;
    }
    try{
      const singleton=['academy','company','fiscal-config'].includes(resource);
      const saved=await write(`/${resource}${record?.id&&!singleton?'/'+record.id:''}`,record?.id||singleton?'PUT':'POST',payload,key);
      notify('Registro salvo com sucesso.');onSaved(saved);
    }catch(e){setError(e.message);}finally{setSaving(false);}
  }
  if(loading)return <Loading/>;
  if(error&&!Object.keys(relations).length&&def.fields.some(x=>x.source))return <ErrorState message={error}/>;
  return <form onSubmit={submit}><div className="form-grid">{fields.map(field=><label key={field.key} className={field.type==='textarea'?'field full':field.type==='checkbox'?'field full check-field':'field'}><span>{field.title}{field.required&&<b> *</b>}</span>{field.type==='textarea'?<textarea aria-label={field.title} value={get(field)} onChange={e=>change(field,e.target.value)} rows={3} maxLength={3000}/>:field.type==='checkbox'?<input type="checkbox" checked={!!get(field)} onChange={e=>change(field,e.target.checked)}/>:['select','relation'].includes(field.type)?<select aria-label={field.title} value={get(field)} required={field.required} onChange={e=>change(field,e.target.value)}>{field.type==='relation'&&<option value="">Selecione…</option>}{field.type==='relation'?options(field).map(option=><option key={option.value} value={option.value}>{option.title}</option>):field.options.map(option=><option key={option} value={option}>{label(option)}</option>)}</select>:<input aria-label={field.title} type={field.type||'text'} value={get(field)} min={field.min} max={field.max} maxLength={field.maxLength||200} minLength={field.minLength} step={field.step} required={field.required} onChange={e=>change(field,e.target.value)}/>} {field.help&&<small>{field.help}</small>}</label>)}</div>{['payments','invoices'].includes(resource)&&<div className="notice">{resource==='payments'?'Registro manual / simulado. Não representa confirmação bancária.':'DOCUMENTO SIMULADO — SEM VALIDADE FISCAL'}</div>}{error&&<div className="form-error" role="alert">{error}</div>}<div className="form-footer"><button type="button" className="button secondary" onClick={onCancel}>Cancelar</button><button className="button" disabled={saving}>{saving&&<LoaderCircle className="spin" size={16}/>} {saving?'Salvando…':'Salvar registro'}</button></div></form>;
}
