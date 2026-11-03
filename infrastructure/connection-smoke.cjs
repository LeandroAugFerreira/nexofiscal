// Confere erros de conexão e o login real. Não emite notas nem envia e-mails.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:5180';
const lines=fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/);
function setting(name){const line=lines.find(x=>x.startsWith(name+'='));if(!line)return '';return line.slice(name.length+1).trim().replace(/^(['"])(.*)\1$/,'$2');}
let browser,stage='startup';
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:1000},locale:'pt-BR'});
 const errors=[];page.on('pageerror',e=>errors.push(e.name));
 await page.goto(base+'/automations',{waitUntil:'domcontentloaded'});
 await page.getByLabel('E-mail',{exact:true}).fill(setting('DEMO_EMAIL'));
 await page.getByLabel('Senha',{exact:true}).fill(setting('DEMO_ADMIN_PASSWORD')||setting('DEMO_PASSWORD'));
 const submit=page.getByRole('button',{name:'Entrar no NexoFiscal',exact:true});
 stage='network error';await page.route('**/api/auth/login',r=>r.abort());await submit.click();
 await page.getByRole('alert').getByText('Não foi possível conectar ao servidor. Verifique se o NexoFiscal está iniciado e tente novamente.',{exact:true}).waitFor();
 assert(await submit.isEnabled());await page.unroute('**/api/auth/login');
 stage='proxy error';await page.route('**/api/auth/login',r=>r.fulfill({status:502,contentType:'text/plain',body:'Proxy unavailable'}));await submit.click();
 await page.getByRole('alert').getByText('O serviço do NexoFiscal está indisponível no momento. Verifique se a API está iniciada e tente novamente.',{exact:true}).waitFor();
 await page.unroute('**/api/auth/login');
 stage='real login';await submit.click();await page.getByRole('heading',{name:'Automações',exact:true}).waitFor();
 assert.equal(await page.locator('.workflow-card').count(),6);
 await page.getByRole('button',{name:'Sair',exact:true}).click();
 await page.getByRole('heading',{name:'Vamos começar?',exact:true}).waitFor();assert.deepEqual(errors,[]);
 console.log('PASS: comunicação via proxy, erro de rede em português, erro 502 em português, nova tentativa e login/logout do Administrador. Sem emissão ou envio.');
})().catch(e=>{console.error('FAIL stage='+stage+' '+e.name+' — credenciais omitidas.');process.exitCode=1;}).finally(async()=>{await browser?.close();});
