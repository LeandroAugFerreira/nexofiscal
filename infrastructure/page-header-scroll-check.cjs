// Valida a estrutura fixa e a rolagem real; não altera cadastros nem envia mensagens.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base='http://127.0.0.1:5180',shots=path.resolve(__dirname,'../artifacts/screenshots/page-headers');
fs.mkdirSync(shots,{recursive:true});
let browser,stage='login';
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:720},locale:'pt-BR'}),errors=[],blocked=[];
 page.on('pageerror',error=>errors.push(error.name));
 await page.route('**/api/**',route=>{
  const request=route.request(),url=new URL(request.url());
  if(!['GET','HEAD'].includes(request.method())&&!['/api/auth/login','/api/auth/logout'].includes(url.pathname)){
   blocked.push(url.pathname);return route.abort();
  }
  return route.continue();
 });
 await page.goto(base);await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).click();
 await page.locator('.page-fixed h1').waitFor();
 const routes=[['/','Central de emissão'],['/emitir','Emitir NFS-e'],['/invoices','Histórico fiscal'],['/clients','Clientes'],['/services','Serviços'],['/company','Empresa emissora'],['/financeiro','Visão financeira'],['/plans','Planos'],['/contracts','Contratos'],['/charges','Cobranças'],['/payments','Pagamentos'],['/reports','Relatórios'],['/fiscal-config','Configuração fiscal'],['/automations','Automações'],['/users','Usuários'],['/audit','Auditoria'],['/system','Sobre e demonstração'],['/account','Minha conta']];
 let scrolled=0;
 const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 async function check(route,title,shot){
  stage=route;await page.goto(base+route);await page.locator('.page-fixed').getByRole('heading',{name:title,exact:true}).waitFor();
  await page.waitForFunction(()=>!document.querySelector('.page-content .state .spin'));await settle();
  const positions=()=>page.evaluate(()=>{
   const fixed=document.querySelector('.page-fixed'),head=fixed.querySelector('.page-head'),tabs=fixed.querySelector('.section-tabs'),body=document.querySelector('.page-scroll');
   return {head:head.getBoundingClientRect().top,subtitle:head.querySelector('.muted').getBoundingClientRect().top,tabs:tabs?.getBoundingClientRect().top,scrollTop:body.scrollTop,bodyTop:body.getBoundingClientRect().top,height:body.clientHeight,windowY:scrollY,overflow:document.documentElement.scrollWidth>innerWidth,inside:body.contains(head)};
  });
  const before=await positions();assert(!before.inside);assert(before.height>140,'Área útil muito pequena.');assert(!before.overflow,'Overflow horizontal da página.');
  await page.locator('.page-scroll').evaluate(el=>el.scrollTop=el.scrollHeight);await settle();const after=await positions();
  assert.equal(after.head,before.head);assert.equal(after.subtitle,before.subtitle);assert.equal(after.tabs,before.tabs);assert.equal(after.windowY,0);
  assert(after.bodyTop>after.subtitle);if(after.scrollTop>0)scrolled++;
  if(shot)await page.screenshot({path:path.join(shots,shot+'.png')});
 }
 for(const [route,title] of routes)await check(route,title,route==='/automations'?'automacoes-desktop':undefined);
 assert(scrolled>=4,'Poucas páginas tiveram rolagem real.');
 await check('/clients','Clientes');await page.getByRole('tab',{name:'Registros',exact:true}).focus();await page.keyboard.press('ArrowRight');
 assert.equal(await page.getByRole('tab',{name:'Indicadores',exact:true}).getAttribute('aria-selected'),'true');
 assert.equal(await page.locator('.page-scroll').evaluate(el=>el.scrollTop),0);
 // Navegação sem recarregar: remove as abas antigas e reinicia apenas o conteúdo.
 await page.locator('.page-scroll').evaluate(el=>el.scrollTop=el.scrollHeight);
 await page.getByRole('navigation',{name:'Navegação principal'}).getByRole('link',{name:'Empresa emissora',exact:true}).click();
 await page.locator('.page-fixed').getByRole('heading',{name:'Empresa emissora',exact:true}).waitFor();
 assert.equal(await page.locator('.page-fixed h1').count(),1);assert.equal(await page.locator('.page-tabbar [role="tablist"]').count(),0);
 assert.equal(await page.locator('.page-scroll').evaluate(el=>el.scrollTop),0);
 await page.getByRole('navigation',{name:'Navegação principal'}).getByRole('link',{name:'Clientes',exact:true}).click();
 await page.locator('.page-fixed').getByRole('heading',{name:'Clientes',exact:true}).waitFor();
 assert.equal(await page.locator('.page-tabbar [role="tablist"]').count(),1);
 const result=await page.request.get(base+'/api/invoices?status=autorizada&page_size=100');assert(result.ok());
 const invoice=(await result.json()).items.find(row=>row.has_pdf);assert(invoice,'Documento simulado de teste indisponível.');
 await check('/invoices/'+invoice.id,invoice.identifier);
 await page.getByRole('button',{name:'E-mail',exact:true}).click();const dialog=page.getByRole('dialog');
 await dialog.getByRole('tab',{name:'Mensagem',exact:true}).waitFor();assert.equal(await dialog.getByRole('tablist').count(),1);
 assert.equal(await page.locator('.page-tabbar [role="tablist"]').count(),1);
 await dialog.getByRole('tab',{name:'Avançado',exact:true}).click();await dialog.getByRole('button',{name:'Baixar mensagem (.eml)',exact:true}).waitFor();
 await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 for(const [route,title] of [['/automations','Automações'],['/users','Usuários'],['/clients','Clientes'],['/fiscal-config','Configuração fiscal'],['/emitir','Emitir NFS-e']])await check(route,title,route==='/automations'?'automacoes-mobile':undefined);
 await page.setViewportSize({width:1440,height:720});await check('/automations','Automações');
 for(const theme of ['Dark','Contraste','Light']){
  await page.getByRole('button',{name:'Tema '+theme,exact:true}).click();await page.locator('.page-scroll').evaluate(el=>el.scrollTop=el.scrollHeight);await settle();
  if(theme==='Dark')await page.screenshot({path:path.join(shots,'automacoes-dark.png')});
 }
 await page.getByRole('button',{name:'Sair',exact:true}).click();assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
 console.log('PASS: 18 telas e detalhe da nota; títulos, subtítulos e abas fora da rolagem; navegação sem recarregar, teclado, diálogos, mobile e temas. Nenhuma emissão ou mensagem enviada.');
})().catch(error=>{console.error('FAIL stage='+stage+' '+error.name+': '+error.message?.slice(0,300));process.exitCode=1;}).finally(async()=>{await browser?.close();});
