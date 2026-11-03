// Dados de leitura fictícios ampliam listas curtas; nenhuma gravação ou SMTP é permitido.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:5180',shots=path.resolve(__dirname,'../artifacts/screenshots/pagination');
fs.mkdirSync(shots,{recursive:true});let browser,activePage,stage='login';
const entries=Array.from({length:25},(_,index)=>({id:9000+index,number:index+1}));
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:900},locale:'pt-BR'}),errors=[],blocked=[];
 activePage=page;
 page.on('pageerror',error=>errors.push(error.name));
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),p=url.pathname;
  if(!['GET','HEAD'].includes(request.method())&&!['/api/auth/login','/api/auth/logout'].includes(p)){blocked.push(p);return route.abort();}
  const fulfill=data=>route.fulfill({json:data});
  if(request.method()==='GET'&&p==='/api/users')return fulfill(entries.map(x=>({id:x.id,name:`Pessoa de teste ${String(x.number).padStart(2,'0')}`,email:`pessoa${x.number}@example.com`,role:x.number%2?'financeiro':'recepcao',active:true})));
  if(/^\/api\/invoices\/\d+\/email$/.test(p))return fulfill({configuration:{configured:true,sender:'remetente@example.com'},items:entries.map(x=>({...x,status:'aceita_smtp',recipient:`destino${x.number}@example.com`,created_at:'2026-10-17T12:00:00',message:'Registro fictício'}))});
  if(/^\/api\/invoices\/\d+\/document$/.test(p))return route.fulfill({contentType:'text/html',body:'<p>Prévia fictícia para teste de paginação.</p>'});
  if(/^\/api\/clients\/\d+\/history$/.test(p))return fulfill({contracts:[],payments:[],invoices:[],charges:entries.map(x=>({...x,code:x.number,amount:'10.00',status:'pendente'}))});
  if(p==='/api/insights/services')return fulfill({metrics:[],distribution:entries.map(x=>({name:'Serviço de teste '+x.number,value:String(x.number)}))});
  if(p==='/api/fiscal/overview'){
   const response=await route.fetch(),data=await response.json();
   data.attention=entries.map(x=>({...x,client_name:'Cliente de teste '+x.number,status:'rejeitada',error:'Pendência fictícia'}));return fulfill(data);
  }
  if(p==='/api/search'&&url.searchParams.get('paginate')==='true'){
   const q=url.searchParams.get('q')||'',number=Number(url.searchParams.get('page')||1),all=q.length>=2&&q!=='nada'?entries:[];
   return fulfill({items:all.slice((number-1)*5,number*5).map(x=>({id:x.id,resource:'services',title:'Resultado de teste '+x.number,description:'Exemplo fictício'})),total:all.length,page:number,page_size:5});
  }
  if(/^\/api\/invoices\/\d+$/.test(p)||p==='/api/automations'){
   const response=await route.fetch();if(!response.ok())return route.fulfill({response});const data=await response.json();
   if(p==='/api/automations')for(const run of data.runs)run.result_data={items:entries.map(x=>({reference:'Item '+x.number,message:'Resultado fictício '+x.number})),total:25};
   else data.events=entries.map(x=>({...x,status:'autorizada',message:'Evento fictício '+x.number,created_at:'2026-10-17T12:00:00'}));
   return fulfill(data);
  }
  return route.continue();
 });
 const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const ready=async()=>{await page.waitForFunction(()=>!document.querySelector('.page-content .state .spin'));await settle();};
 const open=async(route,title)=>{stage=route;await page.goto(base+route);await page.locator('.page-fixed').getByRole('heading',{name:title,exact:true}).waitFor();await ready();};
 const nav=(name,scope=page)=>scope.getByRole('navigation',{name:'Paginação de '+name,exact:true});
 async function move(pager,number){
  await pager.getByRole('button',{name:'Página '+number,exact:true}).click();
  await page.waitForFunction(({name,number})=>{const n=[...document.querySelectorAll('nav.pagination')].find(el=>el.getAttribute('aria-label')===name);return n?.textContent.includes('Página '+number+' de')&&!n.textContent.includes('Carregando');},{name:await pager.getAttribute('aria-label'),number});
  await ready();
 }
 await page.goto(base);await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).click();await page.locator('.page-fixed h1').waitFor();
 for(const [route,title,label] of [['/clients','Clientes','Clientes'],['/contracts','Contratos','Contratos'],['/charges','Cobranças','Cobranças'],['/payments','Pagamentos','Pagamentos'],['/invoices','Histórico fiscal','notas fiscais'],['/audit','Auditoria','auditoria']]){
  await open(route,title);const pager=nav(label),rows=page.locator('.page-content table tbody tr');assert((await rows.count())<=5);const first=await rows.first().innerText();
  const pages=Number((await pager.locator('[role="status"]').innerText()).match(/de (\d+)$/)[1]);
  assert(pages>1);await move(pager,2);assert((await rows.count())<=5);assert.notEqual(await rows.first().innerText(),first);
  if(pages>2)await move(pager,pages);assert((await rows.count())<=5);assert(await pager.getByRole('button',{name:'Próxima página',exact:true}).isDisabled());
  await move(pager,1);assert.equal(await rows.first().innerText(),first);assert(await pager.getByRole('button',{name:'Página anterior',exact:true}).isDisabled());
 }
 await open('/clients','Clientes');await page.locator('.row-actions button[title="Ver detalhes"]').first().click();let dialog=page.getByRole('dialog');
 await dialog.getByRole('button',{name:'Cobranças',exact:true}).click();await dialog.locator('tbody tr').first().waitFor();assert.equal(await dialog.locator('tbody tr').count(),5);
 await move(nav('histórico do cliente',dialog),5);assert.equal(await dialog.locator('tbody tr').count(),5);await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
 await open('/users','Usuários');let pager=nav('usuários');assert.equal(await page.locator('tbody tr').count(),5);await move(pager,5);assert.equal(await page.locator('tbody tr').count(),5);
 await page.getByLabel('Buscar usuários',{exact:true}).fill('teste 25');await settle();assert.equal(await page.locator('tbody tr').count(),1);assert((await nav('usuários').innerText()).includes('Página 1 de 1'));
 await page.getByLabel('Buscar usuários',{exact:true}).fill('');await settle();assert.equal(await page.locator('tbody tr').count(),5);await page.screenshot({path:path.join(shots,'usuarios.png')});
 await open('/','Central de emissão');assert.equal(await page.locator('.attention-item').count(),5);await move(nav('pontos de atenção'),5);assert.equal(await page.locator('.attention-item').count(),5);assert((await nav('notas fiscais').innerText()).includes('Página 1 de'));
 await open('/services','Serviços');await page.getByRole('tab',{name:'Indicadores',exact:true}).click();await page.locator('.recharts-bar-rectangle').first().waitFor();
 assert.equal(await page.locator('.recharts-bar-rectangle').count(),5);await move(nav('Valores dos serviços'),5);assert.equal(await page.locator('.recharts-bar-rectangle').count(),5);
 await open('/automations','Automações');await page.getByRole('tab',{name:/^Histórico/}).click();pager=nav('execuções de automações');assert((await page.locator('tbody tr').count())<=5);
 if(await pager.getByRole('button',{name:'Página 2',exact:true}).count())await move(pager,2);
 await page.getByLabel('Filtrar resultado',{exact:true}).selectOption('sucesso');
 await page.waitForFunction(()=>document.querySelector('nav[aria-label="Paginação de execuções de automações"] [role="status"]')?.textContent.includes('Página 1 de'));
 await ready();assert((await nav('execuções de automações').innerText()).includes('Página 1 de'));
 await page.getByRole('button',{name:'Ver resultado',exact:true}).first().click();dialog=page.getByRole('dialog');assert.equal(await dialog.locator('.routine-result-items article').count(),5);
 await move(nav('itens do resultado',dialog),5);assert.equal(await dialog.locator('.routine-result-items article').count(),5);await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
 await open('/financeiro','Visão financeira');const charges=page.locator('.dashboard-bottom .card').filter({has:page.getByRole('heading',{name:'Últimas cobranças',exact:true})});
 const payments=page.locator('.recent-grid .card').filter({has:page.getByRole('heading',{name:'Últimos pagamentos',exact:true})});
 const notes=page.locator('.recent-grid .card').filter({has:page.getByRole('heading',{name:'Últimas notas simuladas',exact:true})});
 assert.equal(await charges.locator('tbody tr').count(),5);assert.equal(await payments.locator('.recent-item').count(),5);assert.equal(await notes.locator('.recent-item').count(),5);
 const paymentFirst=await payments.locator('.recent-item').first().innerText();await move(nav('Últimas cobranças'),2);assert.equal(await payments.locator('.recent-item').first().innerText(),paymentFirst);assert((await nav('Últimos pagamentos').innerText()).includes('Página 1 de'));
 await page.screenshot({path:path.join(shots,'financeiro.png')});
 const invoices=await (await page.request.get(base+'/api/invoices?status=autorizada&page_size=100')).json(),invoice=invoices.items.find(x=>x.has_pdf);assert(invoice);
 await open('/invoices/'+invoice.id,invoice.identifier);await page.getByRole('tab',{name:'Histórico fiscal',exact:true}).click();assert.equal(await page.locator('.invoice-history .timeline>div').count(),5);
 await move(nav('histórico fiscal'),5);assert.equal(await page.locator('.invoice-history .timeline>div').count(),5);
 await page.getByRole('button',{name:'E-mail',exact:true}).click();dialog=page.getByRole('dialog');await dialog.getByRole('tab',{name:/^Histórico/}).click();await dialog.locator('.delivery-entry').first().waitFor();
 assert.equal(await dialog.locator('.delivery-entry').count(),5);await move(nav('envios de e-mail',dialog),2);assert.equal(await dialog.locator('.delivery-entry').count(),5);await move(nav('envios de e-mail',dialog),5);assert.equal(await dialog.locator('.delivery-entry').count(),5);
 await page.screenshot({path:path.join(shots,'email-historico.png')});await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
 stage='busca';await page.getByRole('button',{name:/^Buscar notas, clientes ou serviços/}).click();dialog=page.getByRole('dialog');await dialog.getByPlaceholder('Identificador, cliente ou serviço…').fill('paginação');await dialog.locator('.search-results a').first().waitFor();
 assert.equal(await dialog.locator('.search-results a').count(),5);await move(nav('resultados da busca',dialog),5);assert.equal(await dialog.locator('.search-results a').count(),5);await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
 await page.setViewportSize({width:390,height:844});await open('/clients','Clientes');await move(nav('Clientes'),2);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:path.join(shots,'clientes-mobile.png')});assert.equal(await page.locator('.sidebar .pagination').count(),0);
 await page.getByRole('button',{name:'Sair',exact:true}).click();await page.getByRole('heading',{name:'Vamos começar?',exact:true}).waitFor();assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
 console.log('PASS: páginas numeradas de 5 itens, última página, filtros, blocos independentes, históricos, busca, diálogos e mobile; menu lateral sem paginação. Nenhuma emissão ou envio.');
})().catch(error=>{console.error('FAIL stage='+stage+' '+error.name+'; detalhes privados omitidos.');process.exitCode=1;}).finally(async()=>{await activePage?.unrouteAll({behavior:'ignoreErrors'});await browser?.close();});
