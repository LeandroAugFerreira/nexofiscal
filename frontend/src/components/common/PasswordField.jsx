import {useState} from 'react';
import {Eye,EyeOff} from 'lucide-react';

export default function PasswordField({label='Senha',value,onChange,required=true,minLength=8,autoComplete='new-password',hint}){
  const [visible,setVisible]=useState(false);
  return <label className="field"><span>{label}</span><div className="password-field"><input aria-label={label} type={visible?'text':'password'} value={value} onChange={e=>onChange(e.target.value)} required={required} minLength={minLength} maxLength={128} autoComplete={autoComplete}/><button type="button" aria-label={`${visible?'Ocultar':'Mostrar'} ${label.toLowerCase()}`} onClick={()=>setVisible(v=>!v)}>{visible?<EyeOff size={18}/>:<Eye size={18}/>}</button></div>{hint&&<small className="muted">{hint}</small>}</label>;
}
