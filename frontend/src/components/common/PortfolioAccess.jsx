import {ArrowRight,Presentation,LoaderCircle} from 'lucide-react';
import {useApi} from '../../hooks/useApi';

export default function PortfolioAccess({onEnter,busy}) {
  const {data}=useApi('/auth/portfolio');
  if(!data?.enabled)return null;
  return <section className="portfolio-access" aria-labelledby="portfolio-title">
    <div className="portfolio-heading"><Presentation size={20}/><div><h3 id="portfolio-title">Conheça o projeto</h3><p>Acesso para portfólio com dados fictícios.</p></div><span className="badge">DEMO</span></div>
    <dl><div><dt>E-mail</dt><dd><code>{data.email}</code></dd></div><div><dt>Senha de demonstração</dt><dd><code>{data.password}</code></dd></div></dl>
    <button type="button" className="button secondary portfolio-button" disabled={busy} onClick={()=>onEnter({email:data.email,password:data.password})}>{busy?<LoaderCircle size={16} className="spin"/>:<Presentation size={16}/>}Entrar no portfólio<ArrowRight size={16}/></button>
    <small>Explore os módulos e teste operações simuladas.</small>
  </section>;
}
