import {createContext, useContext, useEffect, useState} from 'react';
import {api, write, setCsrf} from '../services/api';
const Context = createContext();
export function AuthProvider({children}) {
  const [user,setUser]=useState(null), [loading,setLoading]=useState(true);
  function accept(data) {setCsrf(data?.csrf_token); setUser(data);}
  useEffect(()=> {
    api('/auth/me').then(accept).catch(()=>accept(null)).finally(()=>setLoading(false));
    const expired=()=>accept(null);
    window.addEventListener('nexofiscal:unauthorized',expired);
    return ()=>window.removeEventListener('nexofiscal:unauthorized',expired);
  },[]);
  async function login(data) {accept(await write('/auth/login','POST',data));}
  async function logout() {await write('/auth/logout','POST'); accept(null);}
  async function updateProfile(data) {accept(await write('/auth/me','PUT',data));}
  async function updatePassword(data) {accept(await write('/auth/password','PUT',data));}
  return <Context.Provider value={{user,loading,login,logout,updateProfile,updatePassword,can:permission=>user?.permissions.includes(permission)}}>{children}</Context.Provider>;
}
export const useAuth=()=>useContext(Context);
