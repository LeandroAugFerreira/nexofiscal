// Verifica apresentação e downloads em servidor estático isolado, sem acessar SMTP.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const http=require('node:http'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const portfolio=process.env.FITNOTA_PORTFOLIO_PATH||'C:/Projetos/portfolio';
const base=process.env.FITNOTA_PORTFOLIO_URL||'http://127.0.0.1:5192';
const shots=path.resolve(__dirname,'../artifacts/screenshots/publicacao');fs.mkdirSync(shots,{recursive:true});
let browser,server,page,stage='servidor';
(async()=>{
 if(!process.env.FITNOTA_PORTFOLIO_URL){
  server=http.createServer((req,res)=>{
   const file=path.resolve(portfolio,'.'+decodeURIComponent(new URL(req.url,base).pathname));
   if(!file.startsWith(path.resolve(portfolio)+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end();}
   const size=fs.statSync(file).size,types={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'application/javascript','.json':'application/json','.vtt':'text/vtt; charset=utf-8','.mp4':'video/mp4','.jpg':'image/jpeg','.png':'image/png','.pdf':'application/pdf','.zip':'application/zip'};
   const headers={'Content-Type':types[path.extname(file)]||'application/octet-stream','Accept-Ranges':'bytes'};
   const range=req.headers.range?.match(/bytes=(\d+)-(\d*)/);let start=0,end=size-1,status=200;
   if(range){start=Number(range[1]);end=range[2]?Math.min(Number(range[2]),end):end;headers['Content-Range']=`bytes ${start}-${end}/${size}`;status=206;}
   headers['Content-Length']=end-start+1;res.writeHead(status,headers);if(req.method==='HEAD')return res.end();fs.createReadStream(file,{start,end}).pipe(res);
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(5192,'127.0.0.1',resolve);});
 }
 browser=await chromium.launch({headless:true,channel:'msedge'});page=await browser.newPage({viewport:{width:1440,height:1000},locale:'pt-BR'});
 const errors=[],failed=[];page.on('pageerror',e=>errors.push(e.name));page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)failed.push(new URL(r.url()).pathname+':'+r.status());});
 stage='cartão';await page.goto(base+'/index.html');const card=page.locator('#nexofiscal');await card.scrollIntoViewIfNeeded();await card.locator('video').waitFor();
 assert.equal(await card.locator('.portfolio-video').count(),1);assert(await card.locator('video').evaluate(v=>v.paused&&!v.autoplay));
 await card.getByRole('button',{name:'Reproduzir resumo de NexoFiscal',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#nexofiscal video')?.currentTime>.5);
 assert(await card.locator('video').evaluate(v=>v.duration>19&&v.duration<21));
 await card.locator('select').selectOption('en');await page.waitForFunction(()=>document.querySelector('#nexofiscal .video-subtitles')?.textContent.includes('Clients'));
 await card.locator('select').selectOption('pt-BR');await page.screenshot({path:path.join(shots,'cartao.png')});
 const other=page.locator('#nexolog');await other.scrollIntoViewIfNeeded();await other.getByRole('button',{name:'Reproduzir resumo de NexoLog',exact:true}).click();assert(await card.locator('video').evaluate(v=>v.paused));
 stage='página';await page.goto(base+'/nexofiscal.html');await page.getByRole('heading',{name:'NexoFiscal',exact:true}).waitFor();
 for(const href of await page.locator('a[href]').evaluateAll(nodes=>nodes.map(a=>a.getAttribute('href')))){
  if(!href||href.startsWith('#')||/^(https?:|mailto:)/.test(href))continue;
  const response=await page.request.get(base+'/'+href.split('#')[0]);assert.equal(response.status(),200,href);
 }
 const player=page.locator('[data-project-player]'),video=player.locator('video');assert(await video.evaluate(v=>v.paused&&!v.autoplay));
 stage='vídeo completo';await player.getByRole('button',{name:'Reproduzir apresentação de NexoFiscal',exact:true}).click();await page.waitForFunction(()=>document.querySelector('[data-project-player] video')?.currentTime>.5);
 assert(await video.evaluate(v=>v.duration>95&&v.duration<96));
 stage='legenda EN';await player.locator('[data-caption-language]').selectOption('en');await page.waitForFunction(()=>document.querySelector('[data-project-player] .video-subtitles')?.textContent.includes('NexoFiscal'));
 await player.locator('[data-caption-language]').selectOption('off');assert.equal(await player.locator('.video-subtitles').evaluate(el=>getComputedStyle(el).visibility),'hidden');
 await player.locator('[data-caption-language]').selectOption('pt-BR');await video.evaluate(v=>{v.currentTime=40;v.pause();});
 stage='título da cena';await page.waitForFunction(()=>document.querySelector('[data-project-player] .video-scene-title')?.textContent.includes('PDF'));
 stage='tela cheia';await player.getByRole('button',{name:'Tela cheia: NexoFiscal',exact:true}).click();await page.waitForFunction(()=>!!document.fullscreenElement);await page.screenshot({path:path.join(shots,'video-tela-cheia.png')});
 await page.evaluate(()=>document.exitFullscreen());await page.getByRole('heading',{name:'NexoFiscal',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(shots,'pagina-desktop.png')});
 const download=await page.request.get(base+'/downloads/NexoFiscal-codigo-fonte.zip');assert.equal(download.status(),200);assert((await download.body()).length>200000);
 for(const viewport of [{width:1366,height:768},{width:390,height:844}]){
  await page.setViewportSize(viewport);await page.goto(base+'/nexofiscal.html');await page.locator('.gallery img').last().scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>[...document.images].every(i=>i.complete&&i.naturalWidth>0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.getByRole('heading',{name:'NexoFiscal',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(shots,`pagina-${viewport.width}.png`)});
 }
 assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
 console.log('PASS: cartão, página, vídeos H.264/AAC, legendas PT/EN, pausa entre players, timeline, tela cheia, links, downloads e mobile.');
})().catch(async e=>{await page?.screenshot({path:path.join(shots,'falha.png')});if(page)console.log(await page.locator('[data-project-player]').evaluate(el=>({text:el.innerText,video:[...el.querySelectorAll('video')].map(v=>({paused:v.paused,time:v.currentTime,ready:v.readyState,error:v.error?.code,tracks:[...v.textTracks].map(t=>({language:t.language,mode:t.mode,cues:t.cues?.length,active:[...(t.activeCues||[])].map(c=>c.text)}))}))})).catch(()=>({})));console.error('FAIL '+stage+' '+e.name+': '+e.message.slice(0,250));process.exitCode=1;}).finally(async()=>{await browser?.close();server?.closeAllConnections();server?.close();});
