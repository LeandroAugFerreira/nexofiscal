import {Routes,Route,Navigate} from 'react-router-dom';
import {useAuth} from './contexts/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Account from './pages/Account';
import Records from './pages/Records';
import FiscalCenter from './pages/FiscalCenter';
import IssueInvoice from './pages/IssueInvoice';
import InvoiceDetail from './pages/InvoiceDetail';
import System from './pages/System';
import AppLayout from './layouts/AppLayout';
import {Academy,FiscalConfig,Automations,Reports,Audit,Batches} from './pages/Settings';
import {Loading,ErrorState} from './components/common/Primitives';
function Protected({permission,children}){const {can}=useAuth();return can(permission)?children:<ErrorState message="Seu perfil não permite acessar esta página."/>;}
export default function App(){const {user,loading}=useAuth();if(loading)return <Loading/>;if(!user)return <Login/>;return <Routes><Route element={<AppLayout/>}>
<Route index element={<FiscalCenter/>}/><Route path="emitir" element={<Protected permission="fiscal"><IssueInvoice/></Protected>}/>
<Route path="invoices" element={<FiscalCenter historyOnly/>}/><Route path="invoices/:id" element={<InvoiceDetail/>}/>
<Route path="system" element={<System/>}/>
<Route path="account" element={<Account/>}/>
<Route path="financeiro" element={<Dashboard/>}/>{['clients','plans','services','contracts','charges','payments'].map(resource=><Route key={resource} path={resource} element={<Records key={resource} resource={resource}/>}/>)}
<Route path="company" element={<Academy/>}/><Route path="fiscal-config" element={<FiscalConfig/>}/><Route path="automations" element={<Automations/>}/><Route path="reports" element={<Reports/>}/><Route path="users" element={<Protected permission="users"><Users/></Protected>}/><Route path="audit" element={<Protected permission="audit"><Audit/></Protected>}/><Route path="batches" element={<Batches/>}/>
<Route path="students" element={<Navigate to="/clients" replace/>}/><Route path="academy" element={<Navigate to="/company" replace/>}/><Route path="dashboard" element={<Navigate to="/financeiro" replace/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes>;}
