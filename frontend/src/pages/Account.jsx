import {useState} from 'react';
import {ShieldCheck,LoaderCircle} from 'lucide-react';
import {useAuth} from '../contexts/AuthContext';
import {useUI} from '../contexts/UIContext';
import {PageHeader} from '../components/common/Primitives';
import {Tabs,TabPanel} from '../components/common/Tabs';
import PasswordField from '../components/common/PasswordField';
import {label} from '../utils/format';

function ProfileForm(){
  const {user,updateProfile}=useAuth(),{notify}=useUI();
  const [name,setName]=useState(user.name),[email,setEmail]=useState(user.email),[password,setPassword]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  async function save(event){event.preventDefault();setBusy(true);setError('');try{await updateProfile({name,email,current_password:password});setPassword('');notify('Dados atualizados. Entre novamente nos outros dispositivos.');}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <form className="card account-card" onSubmit={save}><h2>Dados pessoais</h2><p className="account-hint">Seu e-mail também é usado para entrar no sistema.</p><div className="account-fields"><label className="field"><span>Nome completo</span><input required minLength={3} maxLength={120} autoComplete="name" value={name} onChange={e=>setName(e.target.value)}/></label><label className="field"><span>E-mail de acesso</span><input type="email" required maxLength={200} autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)}/></label><PasswordField label="Senha atual" autoComplete="current-password" minLength={1} value={password} onChange={setPassword} hint="Confirme sua senha para salvar os dados."/>{error&&<div className="form-error" role="alert">{error}</div>}</div><div className="account-form-actions"><button className="button" disabled={busy}>{busy&&<LoaderCircle className="spin" size={16}/>}Salvar dados</button></div></form>;
}

function PasswordForm(){
  const {updatePassword}=useAuth(),{notify}=useUI();
  const [current,setCurrent]=useState(''),[password,setPassword]=useState(''),[confirmation,setConfirmation]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function save(event){event.preventDefault();setError('');if(password!==confirmation){setError('A confirmação da senha não confere.');return;}setBusy(true);try{await updatePassword({current_password:current,new_password:password});setCurrent('');setPassword('');setConfirmation('');notify('Senha alterada. As outras sessões foram encerradas.');}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <form className="card account-card" onSubmit={save}><h2>Alterar senha</h2><p className="account-hint">Use de 8 a 128 caracteres. Ao salvar, as outras sessões da sua conta serão encerradas.</p><div className="account-fields"><PasswordField label="Senha atual" autoComplete="current-password" minLength={1} value={current} onChange={setCurrent}/><PasswordField label="Nova senha" value={password} onChange={setPassword}/><PasswordField label="Confirmar nova senha" value={confirmation} onChange={setConfirmation}/>{error&&<div className="form-error" role="alert">{error}</div>}</div><div className="account-form-actions"><button className="button" disabled={busy}>{busy&&<LoaderCircle className="spin" size={16}/>}Salvar nova senha</button></div></form>;
}

export default function Account(){
  const {user}=useAuth(),[tab,setTab]=useState('dados');
  return <><PageHeader eyebrow="PERFIL" title="Minha conta" description="Seus dados de acesso e sua senha."/><div className="account-layout"><section>
    {user.role==='portfolio'?<div className="card account-card"><h2>Conta pública de demonstração</h2><p className="account-hint">Os dados e a senha desta conta são compartilhados para visitas ao portfólio e não podem ser alterados. Para uma conta pessoal, solicite o cadastro ao Administrador.</p><dl className="simple-facts"><div><dt>Nome</dt><dd>{user.name}</dd></div><div><dt>E-mail</dt><dd>{user.email}</dd></div></dl></div>:<><Tabs page id="account" label="Minha conta" tabs={[{value:'dados',label:'Dados pessoais'},{value:'senha',label:'Segurança'}]} value={tab} onChange={setTab}/><TabPanel id="account" value={tab}>{tab==='dados'?<ProfileForm/>:<PasswordForm/>}</TabPanel></>}
    </section><aside className="card account-card account-role"><ShieldCheck size={24}/><h2>{label(user.role)}</h2><p className="account-hint">O perfil define quais operações você pode realizar. A gestão de perfis e acessos é feita pelo Administrador da empresa.</p></aside></div></>;
}
