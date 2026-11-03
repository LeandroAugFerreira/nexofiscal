import {Mail,ArrowRight} from 'lucide-react';
import {Link} from 'react-router-dom';
import {useApi} from '../../hooks/useApi';
import {Loading,ErrorState} from './Primitives';
export default function EmailConfiguration(){
  const {data,loading,error,reload}=useApi('/email/configuration');
  return <section className="card email-configuration"><div className="card-title"><div><h2>Entrega por e-mail</h2><p>Remetente e disponibilidade do envio</p></div><Mail size={21}/></div><div className="email-config-body">
    {loading?<Loading/>:error?<ErrorState message={error} retry={reload}/>:<><span className={`badge ${data.configured?'badge-ativo':'badge-pendente'}`}>{data.configured?'Remetente configurado':'Configuração pendente'}</span><dl className="simple-facts"><div><dt>Remetente</dt><dd>{data.sender||'Não informado'}</dd></div><div><dt>Nome exibido</dt><dd>{data.sender_name||'NexoFiscal'}</dd></div><div><dt>Perfis de envio</dt><dd>Administrador e Financeiro</dd></div></dl><p>A autenticação é conferida ao enviar. O resultado fica no histórico da nota.</p><Link className="text-link" to="/system?tab=tecnico">Informações de configuração<ArrowRight size={14}/></Link></>}
  </div></section>;
}
