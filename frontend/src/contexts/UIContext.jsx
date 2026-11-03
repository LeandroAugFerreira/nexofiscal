import {createContext,useContext,useState,useEffect} from 'react';
import {CheckCircle2,AlertCircle,X} from 'lucide-react';
const Context=createContext();
export function UIProvider({children}) {
  const [theme,setTheme]=useState(()=>{const value=localStorage.getItem('nexofiscal-theme');return ['dark','light','fitness'].includes(value)?value:'light';});
  const [toast,setToast]=useState(null);
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('nexofiscal-theme',theme);},[theme]);
  useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(null),6000);return()=>clearTimeout(timer);},[toast]);
  const notify=(message,type='success')=>setToast({message,type});
  return <Context.Provider value={{theme,setTheme,notify}}>{children}{toast&&<div className={`toast ${toast.type}`} role={toast.type==='error'?'alert':'status'}>{toast.type==='error'?<AlertCircle size={20}/>:<CheckCircle2 size={20}/>}<span>{toast.message}</span><button aria-label="Fechar aviso" onClick={()=>setToast(null)}><X size={16}/></button></div>}</Context.Provider>;
}
export const useUI=()=>useContext(Context);
