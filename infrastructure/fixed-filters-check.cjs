// Confere filtros fora da rolagem; permite somente leituras e login/logout.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:5180',shots=path.resolve(__dirname,'../artifacts/screenshots/fixed-filters');
fs.mkdirSync(shots,{recursive:true});let browser,activePage,stage='login';
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1366,height:768},locale:'pt-BR'}),errors=[],blocked=[];activePage=page;
 page.on('pageerror',error=>errors.push(error.name));
 await page.route('**/api/**',route=>{
  const request=route.request(),url=new URL(request.url());
  if(!['GET','HEAD'].includes(request.method())&&!['/api/auth/login','/api/auth/logout'].includes(url.pathname)){blocked.push(url.pathname);return route.abort();}
  return route.continue();
 });
 const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const ready=async()=>{await page.waitForFunction(()=>!document.querySelector('.page-content .state .spin'));await settle();};
 async function open(route,title){stage=route;await page.goto(base+route);await page.locator('.page-fixed').getByRole('heading',{name:title,exact:true}).waitFor();await ready();}
 async function measure(){return page.evaluate(()=>{
  const filters=document.querySelector('.page-filterbar .page-filters'),header=document.querySelector('.page-fixed'),body=document.querySelector('.page-scroll');
  const rect=filters.getBoundingClientRect();
  return {top:rect.top,bottom:rect.bottom,left:rect.left,right:rect.right,bodyTop:body.getBoundingClientRect().top,bodyHeight:body.clientHeight,inside:body.contains(filters),overflow:document.documentElement.scrollWidth>innerWidth||header.scrollWidth>header.clientWidth+1,scroll:body.scrollTop,max:body.scrollHeight-body.clientHeight};
 });}
 async function verify(shot){
  await page.locator('.page-filterbar .page-filters').waitFor();await ready();const before=await measure();
  assert(!before.inside);assert(!before.overflow,'Filtros escapam lateralmente.');assert(before.bodyHeight>140,'Pouco espaço para os registros.');assert(before.bottom<=before.bodyTop+1);
  const controls=page.locator('.page-filters input,.page-filters select,.page-filters button');for(const control of await controls.all())assert(await control.isEnabled());
  await page.locator('.page-scroll').evaluate(el=>el.scrollTop=el.scrollHeight);await settle();const after=await measure();
  assert.equal(after.top,before.top);assert.equal(after.bottom,before.bottom);
  if(shot)await page.screenshot({path:path.join(shots,shot+'.png')});
 }
 await page.goto(base);await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).click();await page.locator('.page-fixed h1').waitFor();
 const routes=[['/clients','Clientes'],['/services','Serviços'],['/plans','Planos'],['/contracts','Contratos'],['/charges','Cobranças'],['/payments','Pagamentos'],['/','Central de emissão'],['/invoices','Histórico fiscal'],['/users','Usuários'],['/reports','Relatórios']];
 for(const [route,title] of routes){await open(route,title);await verify(route==='/clients'?'clientes-desktop':undefined);}
 await open('/clients','Clientes');const search=page.getByLabel('Pesquisar registros',{exact:true});
 await search.fill('sem resultado filtro 987654');await page.getByRole('button',{name:'Buscar',exact:true}).click();await page.getByText('Nenhum registro por aqui. Ajuste os filtros ou cadastre o primeiro.',{exact:true}).waitFor();assert.equal(await search.inputValue(),'sem resultado filtro 987654');await verify();
 await search.fill('');await page.getByRole('button',{name:'Buscar',exact:true}).click();await page.locator('tbody tr').first().waitFor();
 const pager=page.getByRole('navigation',{name:'Paginação de Clientes',exact:true});await pager.getByRole('button',{name:'Página 2',exact:true}).click();await ready();await verify();
 await page.getByRole('tab',{name:'Indicadores',exact:true}).click();assert.equal(await page.locator('.page-filterbar .page-filters').count(),0);
 await page.getByRole('tab',{name:'Registros',exact:true}).click();await verify();
 await open('/automations','Automações');assert.equal(await page.locator('.page-filterbar .page-filters').count(),0);await page.getByRole('tab',{name:/^Histórico/}).click();await verify('automacoes-desktop');
 await page.getByLabel('Filtrar resultado',{exact:true}).selectOption('sucesso');await page.waitForFunction(()=>document.querySelector('nav[aria-label="Paginação de execuções de automações"] [role="status"]')?.textContent.includes('Página 1 de'));await verify();
 await page.getByRole('tab',{name:/^Rotinas/}).click();assert.equal(await page.locator('.page-filterbar .page-filters').count(),0);
 await page.setViewportSize({width:390,height:844});
 for(const [route,title] of [['/clients','Clientes'],['/invoices','Histórico fiscal'],['/users','Usuários'],['/reports','Relatórios']]){await open(route,title);await verify(route==='/invoices'?'notas-mobile':route==='/reports'?'relatorios-mobile':undefined);}
 await page.getByRole('navigation',{name:'Navegação principal'}).getByRole('link',{name:'Empresa emissora',exact:true}).click();await page.locator('.page-fixed').getByRole('heading',{name:'Empresa emissora',exact:true}).waitFor();assert.equal(await page.locator('.page-filterbar .page-filters').count(),0);
 await page.getByRole('button',{name:'Sair',exact:true}).click();await page.getByRole('heading',{name:'Vamos começar?',exact:true}).waitFor();assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
 console.log('PASS: filtros fixos em dez telas e histórico de automações; busca, páginas, abas, navegação e mobile. Nenhuma emissão ou mensagem enviada.');
})().catch(error=>{console.error('FAIL stage='+stage+' '+error.name+'; detalhes privados omitidos.');process.exitCode=1;}).finally(async()=>{await activePage?.unrouteAll({behavior:'ignoreErrors'});await browser?.close();});
