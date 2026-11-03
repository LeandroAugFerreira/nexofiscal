import {useContext,useEffect,useRef} from 'react';
import {createPortal} from 'react-dom';
import {PageChromeContext} from '../../contexts/PageChromeContext';
import {X,LoaderCircle,Inbox,AlertCircle} from 'lucide-react';
import {label} from '../../utils/format';
export function Badge({value}) {return <span className={`badge badge-${value}`}>{label(value)}</span>;}
export function Loading(){return <div className="state"><LoaderCircle className="spin" size={26}/><p>Carregando informações…</p></div>;}
export function Empty({message='Nenhum registro encontrado.'}){return <div className="state"><Inbox size={32}/><p>{message}</p></div>;}
export function ErrorState({message,retry}){return <div className="state error" role="alert"><AlertCircle size={26}/><p>{message}</p>{retry&&<button className="button secondary" onClick={retry}>Tentar novamente</button>}</div>;}
export function Modal({title,children,onClose,wide=false}){
  const ref=useRef(null);
  useEffect(()=>{const old=document.activeElement;ref.current?.showModal();return()=>{ref.current?.close();old?.focus();};},[]);
  return <dialog ref={ref} className={wide?'modal wide':'modal'} onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===ref.current)onClose();}}><div className="modal-head"><h2>{title}</h2><button type="button" className="icon-button" aria-label="Fechar janela" onClick={onClose}><X/></button></div>{children}</dialog>;
}
export function PageHeader({eyebrow='VISÃO GERAL',title,description,children}){
  const chrome=useContext(PageChromeContext);
  const header=<div className="page-head"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="muted">{description}</p></div><div className="page-actions">{children}</div></div>;
  return chrome?.heading?createPortal(header,chrome.heading):header;
}
