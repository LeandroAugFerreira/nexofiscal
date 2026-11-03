import {useLayoutEffect,useMemo,useRef,useState} from 'react';
import {PageChromeContext} from '../contexts/PageChromeContext';
import FiscalNotice from '../components/common/FiscalNotice';
import Brand from '../components/common/Brand';
import GlobalSearch from '../components/layout/GlobalSearch';
import {NavLink,Link,Outlet,useLocation} from 'react-router-dom';
import {Info,FilePlus2,LayoutDashboard,Users,Dumbbell,FileSignature,Wallet,ArrowDownLeft,Files,ChartNoAxesCombined,Building2,Settings2,Workflow,ShieldCheck,History,PanelLeftClose,PanelLeftOpen,LogOut,ChevronRight,ChevronDown,Sun,Moon,Zap} from 'lucide-react';
import {useAuth} from '../contexts/AuthContext';
import {useUI} from '../contexts/UIContext';
import {useApi} from '../hooks/useApi';
import {label} from '../utils/format';
export const navigation=[
 {title:'EMISSÃO DE NFS-e',items:[['/','Central de emissão',Files],['/emitir','Emitir NFS-e',FilePlus2,'fiscal'],['/invoices','Histórico de notas',History]]},
 {title:'CADASTROS',items:[['/clients','Clientes',Users],['/services','Serviços',FileSignature],['/company','Empresa emissora',Building2]]},
 {title:'FINANCEIRO DE APOIO',collapsible:true,items:[['/financeiro','Visão financeira',LayoutDashboard],['/plans','Planos',Dumbbell],['/contracts','Contratos',FileSignature],['/charges','Cobranças',Wallet],['/payments','Pagamentos',ArrowDownLeft],['/reports','Relatórios',ChartNoAxesCombined]]},
 {title:'ADMINISTRAÇÃO',collapsible:true,items:[['/fiscal-config','Configuração fiscal',Settings2],['/automations','Automações',Workflow],['/users','Usuários',ShieldCheck,'users'],['/audit','Auditoria',History,'audit']]},
];
function MenuGroup({group,can,path}){
 const items=group.items.filter(item=>!item[3]||can(item[3]));
 const links=items.map(([url,title,Icon])=><NavLink end={url==='/'} key={url} to={url} title={title}><Icon size={19}/><span>{title}</span></NavLink>);
 return group.collapsible?<details className="nav-group nav-collapsible" open={items.some(x=>x[0]===path)||undefined}><summary>{group.title}<ChevronDown size={13}/></summary>{links}</details>:<div className="nav-group"><p>{group.title}</p>{links}</div>;
}
export default function AppLayout(){
 const [collapsed,setCollapsed]=useState(false),{user,logout,can}=useAuth(),{theme,setTheme,notify}=useUI();
 const {data:company}=useApi('/company');
 const location=useLocation(),current=navigation.flatMap(g=>g.items).find(x=>x[0]===location.pathname||(x[0]!=='/'&&location.pathname.startsWith(x[0]+'/')));
 const [heading,setHeading]=useState(null),[tabs,setTabs]=useState(null),[filters,setFilters]=useState(null),viewport=useRef(null);
 const chrome=useMemo(()=>({heading,tabs,filters,viewport}),[heading,tabs,filters]);
 useLayoutEffect(()=>{viewport.current?.scrollTo(0,0);},[location.pathname]);
 async function exit(){try{await logout();}catch(e){notify(e.message,'error');}}
 return <div className={`app-shell ${collapsed?'collapsed':''}`}><aside className="sidebar"><NavLink to="/" className="brand"><Brand/></NavLink><div className="workspace"><div className="workspace-icon"><Building2 size={18}/></div><div><strong>{company?.name||'Minha empresa'}</strong><small>Empresa emissora</small></div></div><nav aria-label="Navegação principal">{navigation.map(group=><MenuGroup group={group} key={group.title} can={can} path={location.pathname}/>)}</nav><div className="sidebar-footer"><NavLink to="/system" className="sidebar-about" title="Sobre e demonstração"><Info size={18}/><span>Sobre e demonstração</span></NavLink><button onClick={()=>setCollapsed(v=>!v)} className="collapse-button" aria-label={collapsed?'Expandir menu':'Recolher menu'}>{collapsed?<PanelLeftOpen size={19}/>:<PanelLeftClose size={19}/>}<span>Recolher menu</span></button></div></aside><div className="main-shell"><header className="topbar"><GlobalSearch/><div className="breadcrumbs"><Files size={16}/><span>NexoFiscal</span><ChevronRight size={14}/><strong>{current?.[1]||(location.pathname==='/account'?'Minha conta':'Nota fiscal')}</strong></div><div className="topbar-actions"><div className="theme-switch" aria-label="Temas">{[['dark',Moon,'Dark'],['light',Sun,'Light'],['fitness',Zap,'Contraste']].map(([value,Icon,title])=><button key={value} title={`Tema ${title}`} aria-label={`Tema ${title}`} aria-pressed={theme===value} className={theme===value?'selected':''} onClick={()=>setTheme(value)}><Icon size={16}/></button>)}</div><Link to="/account" className="user account-link" aria-label="Minha conta"><span className="avatar">{user.name.slice(0,1)}</span><div><strong>{user.name.split(' • ')[0]}</strong><small>{label(user.role)}</small></div></Link><button className="icon-button" aria-label="Sair" title="Sair" onClick={exit}><LogOut size={17}/></button></div></header><PageChromeContext.Provider value={chrome}><main className="page-layout"><div className="page-fixed"><FiscalNotice/><div className="page-heading" ref={setHeading}/><div className="page-tabbar" ref={setTabs}/><div className="page-filterbar" ref={setFilters}/></div><div className="page-scroll" ref={viewport} tabIndex={0} role="region" aria-label="Conteúdo da página"><div className="page-content"><Outlet/></div><footer className="app-footer"><span>NexoFiscal</span><Link to="/system">Sobre o projeto</Link></footer></div></main></PageChromeContext.Provider></div></div>;
}
