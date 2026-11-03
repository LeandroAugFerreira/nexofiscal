// Confere encaixe e rolagem em contexto novo, com zoom padrão de 100%.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base='http://127.0.0.1:5180',out=path.resolve(__dirname,'../artifacts/screenshots/scrollbars');
fs.mkdirSync(out,{recursive:true});let browser,stage='login';
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1366,height:768},deviceScaleFactor:1}),errors=[],report=[];
 page.on('pageerror',error=>errors.push(error.name));
 await page.route('**/api/**',route=>{
  const request=route.request(),url=new URL(request.url());
  if(!['GET','HEAD'].includes(request.method())&&!['/api/auth/login','/api/auth/logout'].includes(url.pathname))return route.abort();
  return route.continue();
 });
 await page.goto(base);await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).click();await page.locator('.page-fixed h1').waitFor();
 const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 for(const [width,height] of [[1366,768],[1280,720],[1920,1080],[1024,768],[390,844]]){
  await page.setViewportSize({width,height});
  for(const route of ['/automations','/clients']){
   stage=width+'x'+height+route;await page.goto(base+route);await page.locator('.page-fixed h1').waitFor();await page.waitForFunction(()=>!document.querySelector('.page-content .state .spin'));await settle();
   const data=await page.evaluate(()=>{
    const scroller=document.querySelector('.page-scroll'),nav=document.querySelector('.sidebar nav'),header=document.querySelector('.page-fixed');
    return {viewport:innerWidth,scale:visualViewport.scale,zoom:getComputedStyle(document.documentElement).zoom,documentOverflow:document.documentElement.scrollWidth-innerWidth,contentOverflow:scroller.scrollWidth-scroller.clientWidth,navOverflow:nav.scrollWidth-nav.clientWidth,scrollbar:getComputedStyle(scroller).scrollbarWidth,thumb:getComputedStyle(scroller).scrollbarColor,sidebarThumb:getComputedStyle(nav).scrollbarColor,contentHeight:scroller.clientHeight,headerTop:header.getBoundingClientRect().top,maxScroll:scroller.scrollHeight-scroller.clientHeight};
   });
   assert.equal(data.viewport,width);assert.equal(data.scale,1);assert.equal(Number(data.zoom),1);
   assert(data.documentOverflow<=1,'Página com rolagem horizontal.');assert(data.contentOverflow<=1,'Conteúdo escapou da área de rolagem.');assert(data.navOverflow<=1,'Menu lateral cortado.');
   assert.equal(data.scrollbar,'thin');assert.notEqual(data.thumb,'auto');assert.notEqual(data.sidebarThumb,data.thumb);assert(data.contentHeight>200);
   if(data.maxScroll>0){
    const box=await page.locator('.page-scroll').boundingBox();await page.mouse.move(box.x+box.width-20,box.y+Math.min(100,box.height/2));await page.mouse.wheel(0,500);
    await page.waitForFunction(()=>document.querySelector('.page-scroll').scrollTop>0);
    assert.equal(await page.locator('.page-fixed').evaluate(el=>el.getBoundingClientRect().top),data.headerTop);
   }
   if(route==='/clients')for(const table of await page.locator('.table-wrap').all())await table.evaluate(el=>el.scrollLeft=el.scrollWidth);
   if(route==='/automations'&&[1366,1920,390].includes(width))await page.screenshot({path:path.join(out,width+'x'+height+'.png')});
   report.push({viewport:width+'x'+height,route,...data});
  }
 }
 await page.getByRole('button',{name:'Sair',exact:true}).click();assert.deepEqual(errors,[]);
 fs.writeFileSync(path.resolve(__dirname,'../artifacts/scrollbars-check.json'),JSON.stringify(report,null,2));
 console.log('PASS: 100% em cinco resoluções; barras padronizadas, roda do mouse, cabeçalho fixo e tabelas contidas. Sem alterações de dados ou mensagens.');
})().catch(error=>{console.error('FAIL '+stage+' '+error.name+': '+error.message?.slice(0,250));process.exitCode=1;}).finally(async()=>{await browser?.close();});
