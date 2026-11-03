// Verificação local do formulário de e-mail. Não chama /email-send nem clica em Enviar.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:5180';
const fixture=JSON.parse(fs.readFileSync(path.join(root,'artifacts','primeiro-teste-email.json'),'utf8'));
function setting(key,optional=false){
  const line=fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).find(x=>x.startsWith(key+'='));
  if(!line){if(optional)return '';throw new Error('Configuração de login local ausente.');}
  const value=line.slice(key.length+1).trim();
  return /^(['"]).*\1$/.test(value)?value.slice(1,-1):value;
}
let browser;let stage='startup';
(async()=>{
  browser=await chromium.launch({headless:true,channel:'msedge'});
  const page=await browser.newPage({viewport:{width:1600,height:1000},locale:'pt-BR'});
  const failures=[];page.on('pageerror',()=>failures.push('Erro de interface'));
  let sendAttempt=false;
  // Defesa adicional do teste: qualquer tentativa de envio é abortada antes de chegar à API.
  await page.route('**/api/invoices/*/email-send',route=>{sendAttempt=true;route.abort();});
  await page.goto(base);
  const cfg=await page.request.get(base+'/api/auth/portfolio');assert(cfg.ok());
  const publicAccount=await cfg.json();assert(publicAccount.enabled);
  for(const [role,email,password] of [
    ['administrador',setting('DEMO_EMAIL'),setting('DEMO_ADMIN_PASSWORD',true)||setting('DEMO_PASSWORD')],
    ['financeiro','financeiro@nexofiscal.example.com',setting('DEMO_PASSWORD')],
    ['portfolio',publicAccount.email,publicAccount.password],
  ]){
    stage='login '+role;
    const login=await page.request.post(base+'/api/auth/login',{data:{email,password}});
    assert.equal(login.status(),200,`Login do perfil ${role} não concluído.`);
    stage='document '+role;
    await page.goto(base+`/invoices/${fixture.draft.invoice_id}`);
    await page.getByRole('heading',{name:'Documento demonstrativo',exact:true}).waitFor();
    stage='modal '+role;
    await page.getByRole('button',{name:'E-mail',exact:true}).click();
    stage='sender '+role;
    await page.getByText(fixture.sender,{exact:true}).waitFor();
    stage='permissions '+role;
    const send=page.getByRole('button',{name:'Enviar e-mail',exact:true});
    assert.equal(await send.isDisabled(),role==='portfolio');
    await page.getByRole('tab',{name:'Avançado',exact:true}).click();
    assert(await page.getByRole('button',{name:'Baixar mensagem (.eml)',exact:true}).isEnabled());
    await page.getByRole('tab',{name:'Mensagem',exact:true}).click();
    assert.equal(await page.getByLabel('Destinatário',{exact:true}).inputValue(),fixture.sender);
    if(role==='administrador'){
      await page.screenshot({path:path.join(root,'artifacts','email-interface-ready.png'),fullPage:true});
    }
    stage='logout '+role;
    await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
    await page.getByRole('button',{name:'Sair',exact:true}).click();
    await page.getByRole('heading',{name:'Vamos começar?',exact:true}).waitFor();
  }
  assert.equal(sendAttempt,false);assert.deepEqual(failures,[]);
  console.log('Interface de e-mail verificada: Administrador e Financeiro habilitados; Portfólio bloqueado. Nenhuma chamada de envio.');
})().finally(async()=>{if(browser)await browser.close();}).catch(error=>{console.error(JSON.stringify({stage,error_type:error.name,message:'Verificação não concluída. Credenciais omitidas.'}));process.exitCode=1;});
