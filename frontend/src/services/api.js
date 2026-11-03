let csrf = '';
export const setCsrf = value => {csrf = value || '';};
async function request(path, options = {}) {
  try {
    return await fetch(`/api${path}`, {...options, credentials: 'include', headers: {
      'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...options.headers,
    }});
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Não foi possível conectar ao servidor. Verifique se o NexoFiscal está iniciado e tente novamente.');
  }
}
export async function api(path, options = {}) {
  const response = await request(path, options);
  if (!response.ok) {
    let body;
    try {body = await response.json();} catch {body = {};}
    if (response.status === 401 && path !== '/auth/login') window.dispatchEvent(new Event('nexofiscal:unauthorized'));
    const message = Array.isArray(body.detail) ? body.detail.map(x => `${x.loc?.slice(1).join('.')}: ${x.msg}`).join('; ') : body.detail;
    const unavailable = [500,502,503,504].includes(response.status);
    throw new Error(message || (unavailable ? 'O serviço do NexoFiscal está indisponível no momento. Verifique se a API está iniciada e tente novamente.' : `Não foi possível concluir a operação (HTTP ${response.status}).`));
  }
  return response.status === 204 ? null : response.json();
}
export async function write(path, method, data, key) {
  const result=await api(path, {method, body: data === undefined ? undefined : JSON.stringify(data), headers: key ? {'Idempotency-Key': key} : {}});
  if(!path.startsWith('/auth'))window.dispatchEvent(new Event('nexofiscal:updated'));
  return result;
}
export async function all(resource) {
  const result = [];
  for (let page=1; ;page++) {
    const data = await api(`/${resource}?page_size=100&page=${page}`);
    result.push(...data.items);
    if (result.length >= data.total) return result;
  }
}
export const query = values => new URLSearchParams(Object.entries(values).filter(([,v]) => v !== '' && v !== null && v !== undefined)).toString();
export async function download(path,data,filename){
  const response=await request(path,{method:'POST',body:JSON.stringify(data)});
  if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(typeof body.detail==='string'?body.detail:'Não foi possível preparar o arquivo.');}
  const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
