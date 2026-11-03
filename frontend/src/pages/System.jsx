import {PaginatedItems} from '../components/common/Pagination';
import {useSearchParams,Link} from 'react-router-dom';
import {ArrowRight,FileCheck2,Mail,Info,Settings2} from 'lucide-react';
import {useApi} from '../hooks/useApi';
import {useAuth} from '../contexts/AuthContext';
import {Tabs,TabPanel} from '../components/common/Tabs';
import {PageHeader,Loading,ErrorState,Badge} from '../components/common/Primitives';

function DemoExamples(){
  const {data,loading,error,reload}=useApi('/fiscal/scenarios');
  if(loading)return <Loading/>;
  if(error)return <ErrorState message={error} retry={reload}/>;
  const descriptions={pf:'Pessoa física com CPF cadastrado.',pj:'Pessoa jurídica com CNPJ cadastrado.',rejeicao:'Acompanhe uma rejeição e seu reprocessamento.'};
  return <PaginatedItems items={data.items} label="exemplos de demonstração">{examples=><div className="demo-example-grid">{examples.map(example=><div key={example.id}><h3>{example.title}</h3><p>{descriptions[example.id]}</p>{example.available?<Link className="button secondary" to={`/emitir?scenario=${example.id}`}>Usar exemplo<ArrowRight size={14}/></Link>:<p>{example.reason}</p>}</div>)}</div>}</PaginatedItems>;
}

export default function System(){
  const [params,setParams]=useSearchParams(),{can}=useAuth();
  const tabs=[{value:'ambiente',label:'Ambiente'},{value:'demonstracao',label:'Demonstração'},{value:'tecnico',label:'Informações técnicas'}];
  const value=tabs.some(t=>t.value===params.get('tab'))?params.get('tab'):'ambiente';
  const overview=useApi('/fiscal/overview'),email=useApi('/email/configuration');
  return <><PageHeader eyebrow="NEXOFISCAL" title="Sobre e demonstração" description="Informações do ambiente, exemplos e recursos do projeto."/>
    <Tabs page id="system" label="Informações do projeto" tabs={tabs} value={value} onChange={tab=>setParams({tab})}/>
    <TabPanel id="system" value={value}>
    {value==='ambiente'&&<div className="system-grid">
      <section className="card info-card"><FileCheck2 size={25}/><h2>Ambiente fiscal</h2>
        {overview.loading?<Loading/>:overview.error?<ErrorState message={overview.error} retry={overview.reload}/>:<>
          <Badge value={overview.data.environment}/><p>{overview.data.company_name}</p>
          <dl className="simple-facts"><div><dt>Conexão</dt><dd>{overview.data.connection.connected?'Simulador disponível':'Configuração pendente'}</dd></div><div><dt>Cobranças prontas</dt><dd>{overview.data.ready_charges}</dd></div></dl>
          <Link className="text-link" to="/fiscal-config">Configuração fiscal<ArrowRight size={14}/></Link></>}
      </section>
      <section className="card info-card"><Mail size={25}/><h2>Entrega por e-mail</h2>
        {email.loading?<Loading/>:email.error?<ErrorState message={email.error} retry={email.reload}/>:<>
          <span className={`badge ${email.data.configured?'badge-ativo':'badge-pendente'}`}>{email.data.configured?'Remetente configurado':'Configuração pendente'}</span>
          <p>{email.data.sender||'Nenhum remetente informado'}</p><p className="muted">Administrador e Financeiro podem enviar. O perfil Portfólio pode preparar a mensagem com o PDF.</p>
          <Link className="text-link" to="/fiscal-config?tab=email">Configuração de e-mail<ArrowRight size={14}/></Link></>}
      </section>
      <section className="card info-card full"><Info size={24}/><h2>O que este ambiente representa</h2><p>As notas são documentos simulados, sem validade fiscal. Não há transmissão a prefeitura ou autorização governamental.</p><p>O envio de e-mail é real quando acionado por um perfil autorizado. O PDF mantém a identificação de demonstração.</p></section>
    </div>}
    {value==='demonstracao'&&<div className="system-grid">
      <section className="card info-card full"><span className="eyebrow">EXPLORE A EMISSÃO</span><h2>Escolha um exemplo</h2><p>Os exemplos preenchem o formulário com dados fictícios. Você confere os dados e decide quando emitir.</p>
        {can('fiscal')?<DemoExamples/>:<p className="muted">Os exemplos requerem permissão de emissão.</p>}
      </section>
      <section className="card info-card"><h2>Do cadastro ao documento</h2><ol className="help-steps"><li>Escolha um cliente ativo.</li><li>Informe serviço, valor e competência.</li><li>Revise os dados e confirme a emissão.</li><li>Baixe o PDF ou envie por e-mail.</li></ol></section>
      <section className="card info-card"><h2>Limites da demonstração</h2><p>A emissão individual, os clientes PF/PJ, o histórico e o envio de PDF estão disponíveis. A integração fiscal oficial e a emissão em lote ainda não estão implementadas.</p><p>Pagamentos são registros manuais; não há confirmação automática por banco.</p></section>
    </div>}
    {value==='tecnico'&&<div className="system-grid">
      <section className="card info-card"><Settings2 size={24}/><h2>Documentos e registros</h2><dl className="simple-facts"><div><dt>Versão</dt><dd>0.1.0</dd></div><div><dt>Documentos</dt><dd>PDF, HTML e XML demonstrativo</dd></div><div><dt>Relatórios</dt><dd>CSV com separador ponto e vírgula, em UTF-8</dd></div><div><dt>Identificadores</dt><dd>SIM-ano-número</dd></div><div><dt>Datas de emissão</dt><dd>Horário de Brasília</dd></div></dl><p>O XML utiliza formato próprio de demonstração. Não é um arquivo para transmissão fiscal oficial. Relatórios em Excel e PDF ainda não estão disponíveis.</p></section>
      <section className="card info-card"><Mail size={24}/><h2>SMTP e arquivos de mensagem</h2><p>O envio aceita TLS direto na porta 465 ou STARTTLS na porta 587. “Aceita pelo SMTP” confirma a aceitação pelo servidor; o recebimento deve ser conferido na caixa de destino.</p><p>O arquivo .eml contém a mensagem e o PDF anexo. Para visualizar apenas a nota no navegador, use o PDF.</p>{can('settings')&&<details className="disclosure"><summary>Configurar o remetente</summary><p>Use o assistente local <code>infrastructure/configurar-gmail.ps1</code>. A senha de app é informada na entrada oculta; as credenciais não são exibidas no sistema.</p></details>}</section>
      <section className="card info-card full"><h2>Histórico e proteção contra duplicidade</h2><p>Cada solicitação preserva o resultado, o documento e suas tentativas. Em caso de resultado de envio desconhecido, consulte a caixa de enviados antes de iniciar outra operação.</p><p>Uma nota avulsa não gera cobrança ou pagamento automaticamente. Os registros financeiros e fiscais continuam separados.</p></section>
    </div>}
    </TabPanel>
  </>;
}
