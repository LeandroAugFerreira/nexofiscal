import {Pagination} from '../common/Pagination';
import {useState,useEffect} from 'react';
import {Link} from 'react-router-dom';
import {Search,ArrowUpRight} from 'lucide-react';
import {Modal,Loading,ErrorState,Empty} from '../common/Primitives';
import {useApi} from '../../hooks/useApi';
const names={clients:'Clientes',plans:'Planos',services:'Serviços',charges:'Cobranças',invoices:'Notas simuladas'};
export default function GlobalSearch(){
  const [open,setOpen]=useState(false);
  useEffect(()=>{const listener=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setOpen(v=>!v);}};window.addEventListener('keydown',listener);return()=>window.removeEventListener('keydown',listener);},[]);
  return <><button className="global-search" onClick={()=>setOpen(true)}><Search size={17}/><span>Buscar notas, clientes ou serviços…</span><kbd>Ctrl + K</kbd></button>{open&&<Modal title="Buscar no NexoFiscal" onClose={()=>setOpen(false)}><SearchContent close={()=>setOpen(false)}/></Modal>}</>;
}
function SearchContent({close}){
  const [q,setQ]=useState(''),[search,setSearch]=useState(''),[page,setPage]=useState(1);
  useEffect(()=>{const timer=setTimeout(()=>{setSearch(q);setPage(1);},250);return()=>clearTimeout(timer);},[q]);
  const {data,loading,error}=useApi(`/search?q=${encodeURIComponent(search)}&paginate=true&page=${page}`);
  return <><label className="field"><span>Digite pelo menos dois caracteres</span><input autoFocus placeholder="Identificador, cliente ou serviço…" value={q} onChange={e=>setQ(e.target.value)}/></label>{loading?<Loading/>:error?<ErrorState message={error}/>:data?.items.length?<div className="search-results">{data.items.map(row=><Link key={row.resource+row.id} to={`/${row.resource}?search=${encodeURIComponent(q)}`} onClick={close}><div><strong>{row.title}</strong><small>{names[row.resource]} · {row.description}</small></div><ArrowUpRight size={17}/></Link>)}</div>:<Empty message={q.length<2?'Encontre documentos e cadastros.':'Nenhum resultado encontrado.'}/>}<Pagination page={page} total={data?.total} onChange={setPage} loading={loading||!!error} label="resultados da busca"/></>;
}
