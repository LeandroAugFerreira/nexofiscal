// Verifica a organização das telas sem emitir notas ou enviar e-mail.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:5180';
const shots=path.join(root,'artifacts','screenshots','organization');fs.mkdirSync(shots,{recursive:true});
const fixture=JSON.parse(fs.readFileSync(path.join(root,'artifacts','primeiro-teste-email.json'),'utf8'));
let browser,stage='startup';
(async()=>{
  browser=await chromium.launch({headless:true,channel:'msedge'});
  const page=await browser.newPage({viewport:{width:1600,height:1000},locale:'pt-BR'});
  const errors=[],blocked=[];page.on('pageerror',e=>errors.push(e.name));
  await page.route('**/api/**',route=>{
    const request=route.request(),url=new URL(request.url());
    const allowed=['/api/auth/login','/api/auth/logout','/api/fiscal/preview'];
    if(!['GET','HEAD'].includes(request.method())&&!allowed.includes(url.pathname)&&!url.pathname.endsWith('/email-draft')){
      blocked.push(url.pathname);return route.abort();
    }
    return route.continue();
  });
  const json=async url=>{const r=await page.request.get(base+'/api'+url);assert(r.ok());return r.json();};
  const open=async(route,heading)=>{stage=route;await page.goto(base+route);await page.getByRole('heading',{name:heading,exact:true}).waitFor();};
  const tab=async(name)=>{await page.getByRole('tab',{name,exact:true}).click();};
  const screenshot=async(name)=>{await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(shots,name+'.png'),fullPage:true});};
  await page.goto(base);await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).click();
  await page.getByRole('heading',{name:'Central de emissão',exact:true}).waitFor();
  await page.locator('main .state:has(.spin)').waitFor({state:'hidden'});
  const before=(await json(`/invoices/${fixture.draft.invoice_id}/email`)).items.length;
  assert.equal(await page.locator('.environment-strip').count(),1);
  assert.equal(await page.locator('.fiscal-hero').count(),0);
  assert.equal(await page.getByRole('heading',{name:'Prontidão para emitir',exact:true}).count(),0);
  await screenshot('central');
  await open('/invoices','Histórico fiscal');assert.equal(await page.locator('.fiscal-metrics').count(),0);
  await page.getByLabel('Buscar notas',{exact:true}).fill('Beta');await page.getByRole('button',{name:'Buscar',exact:true}).click();
  await page.getByLabel('Situação das notas',{exact:true}).selectOption('autorizada');
  assert.equal(new URL(page.url()).searchParams.get('search'),'Beta');
  await open('/invoices/'+fixture.draft.invoice_id,fixture.draft.identifier);
  await page.getByRole('heading',{name:'Documento demonstrativo',exact:true}).waitFor();
  assert.equal(await page.locator('.invoice-summary').count(),0);
  await page.frameLocator('iframe').locator('.watermark').waitFor();await screenshot('documento');
  await tab('Dados da nota');await page.getByRole('heading',{name:'Dados da nota',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Solicitar cancelamento',exact:true}).count(),1);
  await page.getByRole('tab',{name:'Dados da nota',exact:true}).focus();await page.keyboard.press('ArrowRight');
  assert.equal(await page.getByRole('tab',{name:'Histórico fiscal',exact:true}).getAttribute('aria-selected'),'true');
  await page.getByRole('heading',{name:'Histórico fiscal',exact:true}).waitFor();
  await page.getByRole('button',{name:'E-mail',exact:true}).click();stage='email';
  await page.getByRole('tab',{name:'Mensagem',exact:true}).waitFor();
  assert(await page.getByRole('button',{name:'Enviar e-mail',exact:true}).isDisabled());
  assert.equal(await page.locator('.delivery-entry').count(),0);await screenshot('email-mensagem');
  await page.getByRole('dialog').getByRole('tab',{name:/^Histórico/}).click();
  await page.getByRole('heading',{name:'Histórico de envio',exact:true}).waitFor();
  assert.equal(await page.locator('.delivery-entry').count(),before);await screenshot('email-historico');
  await tab('Avançado');
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Baixar mensagem (.eml)',exact:true}).click()]);
  assert(download.suggestedFilename().endsWith('.eml'));
  await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
  for(const [route,title] of [['clients','Clientes'],['services','Serviços'],['plans','Planos'],['contracts','Contratos'],['charges','Cobranças'],['payments','Pagamentos']]){
    await open('/'+route,title);assert.equal(await page.locator('.resource-metrics').count(),0);
    await tab('Indicadores');await page.locator('.resource-metrics').waitFor();
    await tab('Registros');assert.equal(await page.locator('.resource-metrics').count(),0);
  }
  await open('/users','Usuários');await tab('Perfis e permissões');await page.getByRole('heading',{name:'Permissões por perfil',exact:true}).waitFor();
  await tab('Indicadores');await page.locator('.resource-metrics').waitFor();
  await open('/fiscal-config','Configuração fiscal');await tab('E-mail');await page.getByRole('heading',{name:'Entrega por e-mail',exact:true}).waitFor();
  await open('/system','Sobre e demonstração');await tab('Informações técnicas');await page.getByRole('heading',{name:'SMTP e arquivos de mensagem',exact:true}).waitFor();
  await tab('Demonstração');await page.getByRole('link',{name:'Usar exemplo',exact:true}).first().waitFor();await screenshot('demonstracao');
  const examples=await page.getByRole('link',{name:'Usar exemplo',exact:true}).all();assert.equal(examples.length,3);await examples[1].click();
  await page.getByRole('heading',{name:'Para quem você está emitindo?',exact:true}).waitFor();
  const expected=(await json('/fiscal/scenarios')).items.find(s=>s.id==='pj').form;
  await page.waitForFunction(id=>document.querySelector('select[aria-label="Cliente / tomador"]')?.value===String(id),expected.client_id);
  assert.equal(await page.locator('.portfolio-scenarios').count(),0);
  await page.getByRole('button',{name:'Continuar',exact:true}).click();await page.getByRole('button',{name:'Revisar dados',exact:true}).click();
  await page.getByRole('heading',{name:'Revise antes de emitir',exact:true}).waitFor();
  assert.equal(await page.getByRole('checkbox').isVisible(),false);
  await page.getByText('Opções de demonstração',{exact:true}).click();assert(await page.getByRole('checkbox').isVisible());
  await screenshot('revisao');
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Revisão móvel com overflow');
  await open('/invoices/'+fixture.draft.invoice_id,fixture.draft.identifier);await page.getByRole('button',{name:'E-mail',exact:true}).click();
  const bounds=await page.getByRole('dialog').boundingBox();assert(bounds.y>=0&&bounds.y+bounds.height<=844);
  assert(await page.getByRole('button',{name:'Enviar e-mail',exact:true}).isVisible());await screenshot('email-mobile');
  await page.getByRole('dialog').getByRole('tab',{name:/^Histórico/}).click();await screenshot('historico-mobile');
  await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
  for(const [route,title] of [['/','Central de emissão'],['/system','Sobre e demonstração'],['/clients','Clientes'],['/users','Usuários'],['/fiscal-config','Configuração fiscal']]){
    await open(route,title);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),route+' móvel com overflow');
  }
  await open('/','Central de emissão');await screenshot('central-mobile');
  await page.setViewportSize({width:1600,height:1000});
  for(const title of ['Dark','Contraste','Light'])await page.getByRole('button',{name:'Tema '+title,exact:true}).click();
  assert.equal((await json(`/invoices/${fixture.draft.invoice_id}/email`)).items.length,before);
  await page.getByRole('button',{name:'Sair',exact:true}).click();await page.getByRole('heading',{name:'Vamos começar?',exact:true}).waitFor();
  assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
  console.log('Organização PASS: Central, abas de documento/dados/histórico, e-mail, indicadores, configurações, exemplos, revisão, teclado, mobile, temas e permissões. Nenhuma nota emitida ou mensagem enviada.');
})().finally(async()=>{if(browser)await browser.close();}).catch(error=>{console.error(JSON.stringify({stage,error_type:error.name,message:error.message?.slice(0,900)}));process.exitCode=1;});
