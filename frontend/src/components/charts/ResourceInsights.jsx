import {PaginatedItems} from '../common/Pagination';
import {Activity,Wallet,Users,FileCheck2,TrendingUp} from 'lucide-react';
import {ResponsiveContainer,PieChart,Pie,Cell,Tooltip,BarChart,Bar,XAxis,YAxis,CartesianGrid} from 'recharts';
import {useApi} from '../../hooks/useApi';
import {money,label} from '../../utils/format';
import {Empty,ErrorState} from '../common/Primitives';
const colors=['#00dca8','#239cf5','#ae87fa','#ffca59','#ff737b','#4ed8dc'];
export function ResourceMetrics({resource}){
  const {data,loading,error}=useApi(`/insights/${resource}`);
  if(error)return <ErrorState message={error}/>;
  return loading?<div className="metrics resource-metrics">{Array.from({length:4},(_,i)=><div className="card metric skeleton" key={i}/>)}</div>:<MetricGrid items={data.metrics}/>;
}
export function MetricGrid({items}){return <div className="metrics resource-metrics">{items.map((item,i)=>{const Icon=[Users,Wallet,Activity,FileCheck2][i%4];return <section className={`card metric ${item.tone||'neutral'}`} key={item.title}><div><span className="metric-icon"><Icon size={24}/></span><span>{item.title}</span></div><strong>{item.kind==='money'?money(item.value):item.kind==='text'?item.value:Number(item.value).toLocaleString('pt-BR')}</strong><p>Estado atual da aplicação</p></section>;})}</div>;}
export function ResourceChart({resource}){
  const {data,loading,error}=useApi(`/insights/${resource}`);
  if(loading||error)return null;
  const series=data.distribution.map(x=>({name:label(x.name),value:Number(x.value)})),bar=['plans','services'].includes(resource);
  const titles={students:'Contratos ativos por plano',clients:'Contratos ativos por plano',plans:'Valores dos planos',services:'Valores dos serviços',contracts:'Contratos por status',charges:'Situação das cobranças',payments:'Distribuição por forma de pagamento',invoices:'Resumo de documentos simulados',users:'Distribuição por perfil de acesso'};
  return <section className="card resource-chart"><div className="card-title"><div><h2>{titles[resource]}</h2><p>{bar?'Valores de cadastro, sem projeção de receita.':'Distribuição dos registros da empresa.'}</p></div><TrendingUp size={19}/></div>{!series.length?<Empty/>:<PaginatedItems items={series} label={titles[resource]} resetKey={resource}>{(pageSeries,{offset})=>bar?<div className="resource-bar"><ResponsiveContainer width="100%" height={230}><BarChart data={pageSeries}><CartesianGrid stroke="var(--border)" vertical={false}/><XAxis dataKey="name" tick={{fill:'var(--muted)',fontSize:11}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'var(--muted)',fontSize:10}} axisLine={false} tickLine={false}/><Tooltip contentStyle={{background:'var(--surface)',border:'1px solid var(--border)'}} formatter={money}/><Bar isAnimationActive={false} dataKey="value" fill="#00dca8" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>:<div className="resource-donut"><ResponsiveContainer width="45%" height={230}><PieChart><Pie isAnimationActive={false} data={series} dataKey="value" innerRadius={68} outerRadius={95} paddingAngle={3} stroke="none">{series.map((x,i)=><Cell fill={colors[i%colors.length]} key={x.name}/>)}</Pie><Tooltip contentStyle={{background:'var(--surface)',border:'1px solid var(--border)'}} formatter={v=>resource==='payments'?money(v):v}/></PieChart></ResponsiveContainer><div className="chart-legend">{pageSeries.map((x,i)=><div key={x.name}><span><i style={{background:colors[(i+offset)%colors.length]}}/>{x.name}</span><strong>{resource==='payments'?money(x.value):x.value}</strong></div>)}</div></div>}</PaginatedItems>}</section>;
}
