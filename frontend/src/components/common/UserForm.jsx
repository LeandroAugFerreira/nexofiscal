import {useState} from 'react';
import {LoaderCircle} from 'lucide-react';
import {Modal} from './Primitives';
import PasswordField from './PasswordField';
import {write} from '../../services/api';
import {useUI} from '../../contexts/UIContext';
import {label} from '../../utils/format';

export const accountRoles=['administrador','financeiro','recepcao','contabilidade'];
export const roleDescriptions={
  administrador:'Gerencia usuários, configurações e todas as operações da empresa.',
  financeiro:'Gerencia cadastros, financeiro, emissão e envio de documentos por e-mail.',
  recepcao:'Cadastra clientes e consulta as informações da empresa.',
  contabilidade:'Consulta documentos, emite NFS-e e acessa a auditoria.',
};

export default function UserForm({account,onClose,onSaved}){
  const editing=Boolean(account),{notify}=useUI();
  const [form,setForm]=useState({name:account?.name||'',email:account?.email||'',role:account?.role||'recepcao',active:account?.active??true,password:'',confirmation:''});
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  function change(key,value){setForm(f=>({...f,[key]:value}));setError('');}
  async function submit(event){
    event.preventDefault();setError('');
    if(form.password!==form.confirmation){setError('A confirmação da senha não confere.');return;}
    setBusy(true);
    try{
      const {confirmation,password,...data}=form;
      if(password)data.password=password;
      await write(editing?`/users/${account.id}`:'/users',editing?'PUT':'POST',data);
      notify(editing?'Conta atualizada.':'Usuário criado. Já é possível entrar com o e-mail e a senha cadastrados.');onSaved();
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <Modal title={editing?'Editar usuário':'Novo usuário'} onClose={()=>{if(!busy)onClose();}}><form className="account-form" onSubmit={submit}>
    <div className="account-fields"><label className="field"><span>Nome completo</span><input autoComplete="off" autoFocus required minLength={3} maxLength={120} value={form.name} onChange={e=>change('name',e.target.value)}/></label>
    <label className="field"><span>E-mail de acesso</span><input type="email" autoComplete="off" required maxLength={200} value={form.email} onChange={e=>change('email',e.target.value)}/></label>
    <div className="account-field-row"><label className="field"><span>Perfil de acesso</span><select aria-label="Perfil de acesso" value={form.role} onChange={e=>change('role',e.target.value)}>{accountRoles.map(role=><option key={role} value={role}>{label(role)}</option>)}</select></label><label className="field"><span>Status da conta</span><select aria-label="Status da conta" value={String(form.active)} onChange={e=>change('active',e.target.value==='true')}><option value="true">Ativa</option><option value="false">Inativa</option></select></label></div>
    <p className="account-hint">{roleDescriptions[form.role]}</p>
    <PasswordField label={editing?'Nova senha (opcional)':'Senha inicial'} value={form.password} onChange={v=>change('password',v)} required={!editing} hint={editing?'Deixe em branco para manter a senha atual.':'Use de 8 a 128 caracteres.'}/>
    <PasswordField label="Confirmar senha" value={form.confirmation} onChange={v=>change('confirmation',v)} required={!editing||Boolean(form.password)}/>
    {editing&&<p className="account-hint">Alterar e-mail, perfil, status ou senha encerra as sessões deste usuário. Contas inativas não conseguem entrar.</p>}
    {error&&<div className="form-error" role="alert">{error}</div>}</div>
    <div className="account-form-actions"><button type="button" className="button secondary" disabled={busy} onClick={onClose}>Cancelar</button><button className="button" disabled={busy}>{busy&&<LoaderCircle className="spin" size={16}/>}Salvar {editing?'alterações':'usuário'}</button></div>
  </form></Modal>;
}
