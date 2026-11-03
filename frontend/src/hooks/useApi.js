import {useState,useEffect,useCallback} from 'react';
import {api} from '../services/api';
export function useApi(path) {
  const [state,setState]=useState({data:null,loading:true,error:null}),[version,setVersion]=useState(0);
  useEffect(()=>{const update=()=>setVersion(v=>v+1);window.addEventListener('nexofiscal:updated',update);return()=>window.removeEventListener('nexofiscal:updated',update);},[]);
  useEffect(()=>{
    let alive=true;
    setState(s=>({...s,loading:true,error:null}));
    api(path).then(data=>{if(alive)setState({data,loading:false,error:null});}).catch(e=>{if(alive)setState({data:null,loading:false,error:e.message});});
    return()=>{alive=false;};
  },[path,version]);
  return {...state,reload:useCallback(()=>setVersion(v=>v+1),[])};
}
