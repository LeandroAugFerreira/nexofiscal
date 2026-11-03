// Confere o editor local sem registrar cookies, senha ou credenciais dos nodes.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:5678';
const lines=fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/);
const setting=key=>{const line=lines.find(x=>x.startsWith(key+'='));return line?line.slice(key.length+1).trim().replace(/^(['"])(.*)\1$/,'$2'):'';};
let browser,page,stage='startup';
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 page=await context.newPage();await page.goto(base+'/signin',{waitUntil:'domcontentloaded'});
 stage='email';
 await page.locator('input[type="email"]').fill(setting('DEMO_EMAIL'));
 stage='password';
 await page.locator('input[type="password"]').fill(setting('DEMO_ADMIN_PASSWORD')||setting('DEMO_PASSWORD'));
 stage='submit';
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 stage='workflows';
 await page.getByText('NexoFiscal — Pagamento confirmado → emitir NFS-e',{exact:true}).first().waitFor({timeout:60000});
 const names=fs.readdirSync(path.join(root,'n8n','workflows')).filter(x=>x.endsWith('.json')).map(x=>JSON.parse(fs.readFileSync(path.join(root,'n8n','workflows',x),'utf8')).name);
 assert.equal(names.length,6);
 for(const name of names)await page.getByText(name,{exact:true}).first().waitFor();
 assert.equal(await page.getByText('Published',{exact:true}).count(),6);
 const directory=path.join(root,'artifacts','screenshots','n8n');fs.mkdirSync(directory,{recursive:true});
 await page.screenshot({path:path.join(directory,'editor-workflows.png'),fullPage:true});
 console.log('PASS: login no editor local e lista de workflows acessíveis. Credenciais omitidas.');
})().catch(async error=>{console.error('FAIL editor stage='+stage+': '+error.name+'; dados privados omitidos.');if(page){console.log('Path:',new URL(page.url()).pathname);console.log('Inputs:',await page.locator('input').evaluateAll(xs=>xs.map(x=>({type:x.type,name:x.name,placeholder:x.placeholder}))));console.log('Buttons:',await page.getByRole('button').allTextContents());}process.exitCode=1;}).finally(async()=>{await browser?.close();});
