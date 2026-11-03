const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:5180',backend='http://127.0.0.1:8011';
const shots=path.resolve(__dirname,'../artifacts/screenshots/automations');fs.mkdirSync(shots,{recursive:true});
let browser,page,stage='startup';
(async()=>{
  browser=await chromium.launch({headless:true,channel:'msedge'});
  page=await browser.newPage({viewport:{width:1440,height:1000},locale:'pt-BR'});
  const errors=[],blocked=[];page.on('pageerror',e=>errors.push(e.name));
  await page.route('**/api/**',route=>{
    const r=route.request(),url=new URL(r.url());
    if(!['GET','HEAD'].includes(r.method())&&!/^\/api\/(auth\/(login|logout)|automations\/\d+(\/run)?|invoices\/\d+\/email-draft)$/.test(url.pathname)){
      blocked.push(url.pathname);return route.abort();
    }
    return route.continue({url:backend+url.pathname+url.search});
  });
  const shot=async name=>{await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(shots,name+'.png'),fullPage:true});};
  await page.goto(base+'/automations');await page.getByLabel('E-mail',{exact:true}).fill('admin@example.com');await page.getByLabel('Senha',{exact:true}).fill('Automations-QA-admin-123');await page.getByRole('button',{name:'Entrar no NexoFiscal',exact:true}).click();
  await page.getByRole('heading',{name:'Automações',exact:true}).waitFor();assert.equal(await page.locator('.workflow-card').count(),6);await shot('rotinas-iniciais');
  const workflows=await page.locator('.workflow-card h2').allTextContents();
  for(const name of workflows){
    stage=name;const card=page.locator('.workflow-card').filter({has:page.getByRole('heading',{name,exact:true})});
    assert(await card.getByRole('button',{name:'Executar '+name,exact:true}).isDisabled());
    await card.getByRole('button',{name:'Ativar '+name,exact:true}).click();
    await card.getByRole('button',{name:'Executar '+name,exact:true}).click();
    const dialog=page.getByRole('dialog');await dialog.getByRole('heading',{name:'Executar rotina',exact:true}).waitFor();
    await dialog.getByRole('button',{name:'Executar agora',exact:true}).waitFor();
    if(await dialog.getByRole('combobox').count()){
      await dialog.getByRole('combobox').locator('option').nth(1).waitFor({state:'attached'});
      const value=await dialog.getByRole('combobox').locator('option').nth(1).getAttribute('value');await dialog.getByRole('combobox').selectOption(value);
    }
    await dialog.getByRole('button',{name:'Executar agora',exact:true}).click();
    await page.getByRole('heading',{name:'Resultado da rotina',exact:true}).waitFor();await page.locator('.routine-result .badge').getByText('Concluída',{exact:true}).waitFor();
    if(name.startsWith('Documento')){
      const [file]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Baixar mensagem (.eml)',exact:true}).click()]);assert(file.suggestedFilename().endsWith('.eml'));
    }
    if(name.startsWith('Fechamento'))await shot('fechamento');
    await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
  }
  stage='history';await page.getByRole('tab',{name:/^Histórico/}).click();assert.equal(await page.getByRole('button',{name:'Ver resultado',exact:true}).count(),6);await shot('historico');
  await page.getByRole('button',{name:'Ver resultado',exact:true}).first().click();
  const [jsonResult]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Baixar resultado JSON',exact:true}).click()]);assert(jsonResult.suggestedFilename().endsWith('.json'));
  await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
  stage='connection';await page.getByRole('tab',{name:'Conexão n8n',exact:true}).click();await page.getByRole('heading',{name:'n8n não configurado',exact:true}).waitFor();
  await page.getByLabel('Destino dos workflows',{exact:true}).selectOption('docker');
  const [workflowFile]=await Promise.all([page.waitForEvent('download'),page.locator('.workflow-download-list a').first().click()]);assert(workflowFile.suggestedFilename().endsWith('.json'));await shot('conexao');
  stage='sticky';await page.setViewportSize({width:1440,height:500});
  await page.locator('.sidebar .nav-collapsible').evaluateAll(nodes=>nodes.forEach(n=>n.open=true));
  for(const name of ['FINANCEIRO DE APOIO','ADMINISTRAÇÃO']){
    const summary=page.locator('.sidebar summary').filter({hasText:name});
    const measurement=await summary.evaluate(el=>{const nav=el.closest('nav');nav.scrollTop=0;nav.scrollTop=el.getBoundingClientRect().top-nav.getBoundingClientRect().top+15;return {position:getComputedStyle(el).position,top:el.getBoundingClientRect().top,navTop:nav.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom,navBottom:nav.getBoundingClientRect().bottom};});
    assert.equal(measurement.position,'sticky');assert(measurement.top>=measurement.navTop-1);assert(measurement.bottom<=measurement.navBottom+1);
  }
  await shot('menu-fixo');
  stage='mobile';await page.setViewportSize({width:390,height:844});await page.getByRole('tab',{name:/^Rotinas/}).click();await shot('rotinas-mobile');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  await page.getByRole('button',{name:'Sair',exact:true}).click();
  assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
  console.log('PASS: seis rotinas locais, ativação, resultados/histórico, downloads, diagnóstico n8n, cabeçalhos fixos e mobile. Nenhum e-mail enviado.');
})().catch(async error=>{console.error('FAIL stage='+stage+' '+error.message);if(page)await page.screenshot({path:path.join(shots,'failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}).finally(async()=>{await browser?.close();});
