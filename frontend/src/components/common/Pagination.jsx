import {useEffect,useState} from 'react';

export const PAGE_SIZE=5;

function pageNumbers(page,total){
  if(total<=7)return Array.from({length:total},(_,index)=>index+1);
  const values=[1,...Array.from({length:3},(_,index)=>Math.min(Math.max(page-1,2),total-3)+index),total];
  const result=[];
  for(const value of [...new Set(values)].sort((a,b)=>a-b)){
    if(result.length&&value-result[result.length-1]>1)result.push('gap-'+value);
    result.push(value);
  }
  return result;
}

export function Pagination({page,total,onChange,loading=false,label='registros'}){
  const pages=Math.max(1,Math.ceil((total||0)/PAGE_SIZE)),current=Math.min(page,pages);
  useEffect(()=>{if(total!==undefined&&!loading&&page>pages)onChange(pages);},[total,loading,page,pages,onChange]);
  const start=total?(current-1)*PAGE_SIZE+1:0,end=Math.min(current*PAGE_SIZE,total||0);
  return <nav className="pagination" aria-label={`Paginação de ${label}`}>
    <span role="status" aria-live="polite">{loading?'Carregando…':`${start}–${end} de ${total||0} itens · Página ${current} de ${pages}`}</span>
    <div className="pagination-controls">
      <button type="button" className="button secondary small" aria-label="Página anterior" disabled={loading||current<=1} onClick={()=>onChange(current-1)}>Anterior</button>
      {pageNumbers(current,pages).map(value=>typeof value==='number'?<button type="button" key={value} className="button secondary small page-number" aria-label={`Página ${value}`} aria-current={current===value?'page':undefined} disabled={loading||current===value} onClick={()=>onChange(value)}>{value}</button>:<span key={value} className="pagination-gap" aria-hidden="true">…</span>)}
      <button type="button" className="button secondary small" aria-label="Próxima página" disabled={loading||current>=pages} onClick={()=>onChange(current+1)}>Próxima</button>
    </div>
  </nav>;
}

// Cada bloco mantém sua página; filtros trocam a chave e retornam à primeira.
export function PaginatedItems({items=[],label,resetKey='',children}){
  const [position,setPosition]=useState({key:resetKey,page:1});
  const pages=Math.max(1,Math.ceil(items.length/PAGE_SIZE));
  useEffect(()=>{setPosition(previous=>previous.key!==resetKey?{key:resetKey,page:1}:previous.page>pages?{...previous,page:pages}:previous);},[pages,resetKey]);
  const page=position.key===resetKey?Math.min(position.page,pages):1,offset=(page-1)*PAGE_SIZE;
  return <>{children(items.slice(offset,offset+PAGE_SIZE),{page,offset})}{items.length>0&&<Pagination page={page} total={items.length} label={label} onChange={value=>setPosition({key:resetKey,page:value})}/>}</>;
}
