const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),path=require('node:path');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:500}});
 await page.route('**/api/**',r=>{const u=new URL(r.request().url());return r.continue({url:'http://127.0.0.1:8011'+u.pathname+u.search});});
 await page.goto('http://127.0.0.1:5180/automations',{waitUntil:'domcontentloaded'});await page.getByLabel('E-mail',{exact:true}).fill('admin@example.com');await page.getByLabel('Senha',{exact:true}).fill('Automations-QA-admin-123');await page.getByRole('button',{name:'Entrar no NexoFiscal',exact:true}).click();await page.getByRole('heading',{name:'Automações',exact:true}).waitFor();
 await page.locator('.sidebar .nav-collapsible').evaluateAll(nodes=>nodes.forEach(n=>n.open=true));
 for(const [label,name] of [['FINANCEIRO DE APOIO','financeiro-fixo'],['ADMINISTRAÇÃO','administracao-fixo']]){
  const summary=page.locator('.sidebar summary').filter({hasText:label});
  await summary.evaluate(el=>{const nav=el.closest('nav');nav.scrollTop=0;nav.scrollTop=el.getBoundingClientRect().top-nav.getBoundingClientRect().top+15;});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const measurement=await summary.evaluate(el=>{const nav=el.closest('nav');return {label:el.textContent,top:el.getBoundingClientRect().top,navTop:nav.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom,navBottom:nav.getBoundingClientRect().bottom,scrollTop:nav.scrollTop,maxScroll:nav.scrollHeight-nav.clientHeight};});
  console.log(JSON.stringify(measurement));assert(Math.abs(measurement.top-measurement.navTop)<2);
  await page.screenshot({path:path.resolve(__dirname,'../artifacts/screenshots/automations/'+name+'.png')});
 }
 await page.getByRole('button',{name:'Sair',exact:true}).click();console.log('PASS: cabeçalhos Financeiro e Administração fixos na rolagem.');
})().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(async()=>{await browser?.close();});
