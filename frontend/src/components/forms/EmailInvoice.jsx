import {PaginatedItems} from '../common/Pagination';
import {useState} from 'react';
import {FileText,Download,Send,LoaderCircle} from 'lucide-react';
import {Link} from 'react-router-dom';
import {useApi} from '../../hooks/useApi';
import {useAuth} from '../../contexts/AuthContext';
import {useUI} from '../../contexts/UIContext';
import {write,download} from '../../services/api';
import {Modal,Loading,ErrorState,Empty} from '../common/Primitives';
import {Tabs,TabPanel} from '../common/Tabs';
import {dateTime} from '../../utils/format';

const statuses={aceita_smtp:'Aceita pelo SMTP',falhou:'Falha no envio',preparando:'Preparando',enviando:'Em envio',resultado_desconhecido:'Resultado não confirmado'};
export default function EmailInvoice({invoice,onClose}){
  const {can}=useAuth(),{notify}=useUI(),{data,loading,error:loadError,reload}=useApi(`/invoices/${invoice.id}/email`);
  const [tab,setTab]=useState('mensagem'),[recipient,setRecipient]=useState('cliente.nfse.portifolio@gmail.com');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState(null),[key]=useState(()=>crypto.randomUUID());
  const configured=data?.configuration.configured;
  const tabs=[{value:'mensagem',label:'Mensagem'},{value:'historico',label:'Histórico',count:data?.items.length??0},{value:'avancado',label:'Avançado'}];
  async function prepare(){setBusy(true);setError('');try{await download(`/invoices/${invoice.id}/email-draft`,{recipient},`${invoice.identifier}-mensagem.eml`);}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function send(event){
    event.preventDefault();if(tab!=='mensagem'||busy||!configured||!can('email_send')||result)return;
    setBusy(true);setError('');try{
      const row=await write(`/invoices/${invoice.id}/email-send`,'POST',{recipient},key);
      setResult(row);setTab('historico');reload();notify(statuses[row.status]||'Resultado de envio registrado.',row.status==='aceita_smtp'?'success':'error');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <Modal title="Enviar documento por e-mail" onClose={onClose}>
    <form className="email-compose" onSubmit={send}>
      <Tabs id="email" label="Opções de e-mail" tabs={tabs} value={tab} onChange={setTab}/>
      <TabPanel id="email" value={tab}>
        {loadError&&<ErrorState message={loadError} retry={reload}/>}
        {tab==='mensagem'&&<>
          <label className="field"><span>Destinatário</span><input aria-label="Destinatário" type="email" required value={recipient} onChange={e=>setRecipient(e.target.value)} placeholder="cliente@empresa.com"/></label>
          <div className="email-attachment"><FileText size={23}/><div><strong>{invoice.identifier}-demonstracao.pdf</strong><small>PDF anexo · sem validade fiscal</small></div></div>
          <dl className="email-message-facts"><div><dt>Remetente</dt><dd>{data?.configuration.sender||'Verificando…'}</dd></div><div><dt>Assunto</dt><dd>[DEMONSTRAÇÃO] Documento de serviço {invoice.identifier} | NexoFiscal</dd></div></dl>
          {!loading&&!loadError&&!configured&&<div className="notice">Configure o remetente antes de enviar. Você pode baixar a mensagem na aba Avançado.</div>}
          {!can('email_send')&&<div className="notice">Seu perfil permite preparar a mensagem. O envio está disponível para Administrador e Financeiro.</div>}
          {result&&<p className="muted">Esta tentativa já foi registrada. Consulte a aba Histórico.</p>}
        </>}
        {tab==='historico'&&<>
          <h3 className="panel-heading">Histórico de envio</h3>
          {loading?<Loading/>:data?.items.length?<PaginatedItems items={data.items} label="envios de e-mail" resetKey={invoice.id}>{deliveries=><div className="delivery-list">{deliveries.map(row=><article key={row.id} className={`delivery-entry ${row.status==='aceita_smtp'?'accepted':''}`}><div><strong>{statuses[row.status]||row.status}</strong><time>{dateTime(row.created_at)}</time></div><p>{row.recipient}</p>{row.status!=='aceita_smtp'&&<small>{row.message}</small>}</article>)}</div>}</PaginatedItems>:!loadError&&<Empty message="Nenhum envio registrado para este documento."/>}
          {!!data?.items.length&&<p className="email-draft-hint">A aceitação pelo SMTP não confirma a chegada à caixa de entrada. Confira o recebimento no destino.</p>}
        </>}
        {tab==='avancado'&&<div className="email-advanced"><h3 className="panel-heading">Arquivo de mensagem</h3><p>Baixe o e-mail com o PDF anexo em formato .eml. Esse arquivo é destinado a aplicativos de e-mail; para ver apenas a nota no navegador, use o PDF.</p><button type="button" className="button secondary" onClick={prepare} disabled={busy||loading}>{busy?<LoaderCircle className="spin" size={16}/>:<Download size={16}/>}Baixar mensagem (.eml)</button><Link className="text-link" to="/system?tab=tecnico" onClick={onClose}>Sobre formatos e envio</Link></div>}
        {error&&<div className="form-error" role="alert">{error}</div>}
      </TabPanel>
      <div className="email-modal-actions"><button type="button" className="button secondary" onClick={onClose}>Fechar</button>{tab==='mensagem'&&<button className="button" disabled={busy||loading||!configured||!can('email_send')||!!result}>{busy?<LoaderCircle className="spin" size={16}/>:<Send size={16}/>}Enviar e-mail</button>}</div>
    </form>
  </Modal>;
}
