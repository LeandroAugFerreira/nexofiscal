import PageFilters from '../components/common/PageFilters';
import {Pagination,PaginatedItems} from '../components/common/Pagination';
import {useState} from 'react';
import {Search,ShieldCheck,Plus,Pencil} from 'lucide-react';
import {Link} from 'react-router-dom';
import {useAuth} from '../contexts/AuthContext';
import UserForm from '../components/common/UserForm';
import {useApi} from '../hooks/useApi';
import {dateTime,label} from '../utils/format';
import {PageHeader,Loading,ErrorState,Badge,Empty} from '../components/common/Primitives';
import {Tabs,TabPanel} from '../components/common/Tabs';
import {ResourceMetrics,ResourceChart} from '../components/charts/ResourceInsights';

export default function Users(){
  const {user}=useAuth(),editable=user.role==='administrador';
  const {data,loading,error,reload}=useApi('/users');
  const [form,setForm]=useState(null);
  const [tab,setTab]=useState('usuarios'),[q,setQ]=useState(''),[role,setRole]=useState(''),[status,setStatus]=useState('');
  const rows=(data||[]).filter(row=>(row.name+' '+row.email).toLowerCase().includes(q.toLowerCase())&&(!role||row.role===role)&&(!status||String(row.active)===status));
  return <><PageHeader eyebrow="ADMINISTRAÇÃO" title="Usuários" description="Gerencie as contas e os perfis de acesso da empresa.">{editable&&<button className="button" onClick={()=>setForm({})}><Plus size={17}/>Novo usuário</button>}</PageHeader>
    <Tabs page id="users" label="Gestão de usuários" tabs={[{value:'usuarios',label:'Usuários'},{value:'perfis',label:'Perfis e permissões'},{value:'indicadores',label:'Indicadores'}]} value={tab} onChange={setTab}/>
    <TabPanel id="users" value={tab}>
    {tab==='usuarios'&&<><p className="account-list-hint">{editable?'Crie uma conta com e-mail e senha para cada pessoa. Para remover o acesso, edite e desative a conta.':'A criação e a alteração de contas são exclusivas do Administrador. A conta de portfólio permite consultar esta tela.'}</p><section className="card"><div className="card-title"><h2>Lista de usuários</h2><ShieldCheck size={20}/></div>
      <PageFilters label="Filtros de usuários"><div className="table-toolbar"><label className="search-box"><Search size={17}/><input aria-label="Buscar usuários" placeholder="Buscar por nome ou e-mail…" value={q} onChange={e=>setQ(e.target.value)}/></label><select aria-label="Filtrar perfil" value={role} onChange={e=>setRole(e.target.value)}><option value="">Todos os perfis</option>{['administrador','financeiro','recepcao','contabilidade','portfolio'].map(x=><option key={x} value={x}>{label(x)}</option>)}</select><select aria-label="Filtrar acesso" value={status} onChange={e=>setStatus(e.target.value)}><option value="">Todos os acessos</option><option value="true">Ativos</option><option value="false">Inativos</option></select></div></PageFilters>
      {loading?<Loading/>:error?<ErrorState message={error} retry={reload}/>:rows.length?<PaginatedItems items={rows} label="usuários" resetKey={`${q}|${role}|${status}`}>{pageRows=><div className="table-wrap"><table><thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Último acesso</th><th>Status</th><th>Ações</th></tr></thead><tbody>{pageRows.map(row=><tr key={row.id}><td className="name-cell"><span className="table-name"><span className="mini-avatar">{row.name.slice(0,2).toUpperCase()}</span>{row.name}</span></td><td>{row.email}</td><td>{label(row.role)}</td><td>{row.last_login?dateTime(row.last_login):'Sem acesso registrado'}</td><td><Badge value={row.active?'ativo':'inativo'}/></td><td>{row.id===user.id?<Link className="text-link" to="/account">Minha conta</Link>:editable&&row.role!=='portfolio'?<button className="icon-button" title={`Editar ${row.name}`} aria-label={`Editar ${row.name}`} onClick={()=>setForm(row)}><Pencil size={16}/></button>:<span className="muted">—</span>}</td></tr>)}</tbody></table></div>}</PaginatedItems>:<Empty/>}
    </section></>}
    {tab==='perfis'&&<section className="card"><div className="card-title"><h2>Permissões por perfil</h2></div><div className="table-wrap"><table><thead><tr><th>Perfil</th><th>Acesso</th></tr></thead><tbody>{[
      ['Administrador','Cadastros, financeiro, emissão e cancelamento, envio de e-mail, configurações, automações e auditoria.'],
      ['Financeiro','Cadastros, financeiro, emissão, envio de e-mail e automações.'],
      ['Recepção','Cadastro de clientes e consulta aos módulos.'],
      ['Contabilidade','Consulta, emissão e auditoria.'],
      ['Portfólio','Operações demonstrativas. O envio real de e-mail e a gestão de contas são bloqueados.'],
    ].map(([name,text])=><tr key={name}><td className="name-cell">{name}</td><td className="wrap-cell">{text}</td></tr>)}</tbody></table></div></section>}
    {tab==='indicadores'&&<><ResourceMetrics resource="users"/><ResourceChart resource="users"/></>}
    </TabPanel>
    {form&&<UserForm account={form.id?form:null} onClose={()=>setForm(null)} onSaved={()=>{setForm(null);reload();}}/>}
  </>;
}
