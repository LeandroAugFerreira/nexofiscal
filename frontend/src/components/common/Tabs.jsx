import {useContext,useLayoutEffect,useRef} from 'react';
import {createPortal} from 'react-dom';
import {PageChromeContext} from '../../contexts/PageChromeContext';

export function Tabs({id,label,tabs,value,onChange,page=false}) {
  const buttons=useRef([]);
  const chrome=useContext(PageChromeContext),viewport=chrome?.viewport;
  useLayoutEffect(()=>{if(page&&viewport?.current)viewport.current.scrollTo(0,0);},[page,value,viewport]);
  function navigate(event,index) {
    let next;
    if(event.key==='ArrowRight')next=(index+1)%tabs.length;
    else if(event.key==='ArrowLeft')next=(index-1+tabs.length)%tabs.length;
    else if(event.key==='Home')next=0;
    else if(event.key==='End')next=tabs.length-1;
    else return;
    event.preventDefault();onChange(tabs[next].value);buttons.current[next]?.focus();
  }
  const tablist=<div className="section-tabs" role="tablist" aria-label={label}>{tabs.map((tab,index)=><button
    key={tab.value} ref={node=>buttons.current[index]=node} type="button" role="tab"
    id={`${id}-${tab.value}-tab`} aria-controls={`${id}-${tab.value}-panel`}
    aria-selected={value===tab.value} tabIndex={value===tab.value?0:-1}
    onClick={()=>onChange(tab.value)} onKeyDown={event=>navigate(event,index)}>
    {tab.label}{tab.count!==undefined&&<span className="tab-count">{tab.count}</span>}
  </button>)}</div>;
  return page&&chrome?.tabs?createPortal(tablist,chrome.tabs):tablist;
}

export function TabPanel({id,value,children,className=''}) {
  return <section className={`tab-panel ${className}`} role="tabpanel" id={`${id}-${value}-panel`}
    aria-labelledby={`${id}-${value}-tab`} tabIndex={0}>{children}</section>;
}
