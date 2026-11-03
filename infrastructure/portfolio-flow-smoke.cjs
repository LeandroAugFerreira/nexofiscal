// Captura a interface atual e valida a jornada. Nunca transmite e-mail.
const {chromium}=require(process.env.FITNOTA_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=process.env.FITNOTA_DEMO_URL||'http://127.0.0.1:5180';
const output=path.resolve(__dirname,'../artifacts/portfolio-demo');
fs.mkdirSync(output,{recursive:true});let browser,page,stage='login';
const scenes=[];
(async()=>{
 browser=await chromium.launch({headless:true,channel:'msedge'});
 page=await browser.newPage({viewport:{width:1600,height:1000},locale:'pt-BR'});
 const errors=[],blocked=[];page.on('pageerror',e=>errors.push(e.name));
 await page.route('**/api/**',route=>{
  if(/\/email-send(?:\?|$)/.test(route.request().url())){blocked.push('email-send');return route.abort();}
  return route.continue();
 });
 const ready=async()=>{await page.waitForFunction(()=>!document.querySelector('main .state .spin'));await page.evaluate(()=>document.fonts.ready);};
 async function scene(id,title){stage=id;await ready();await page.screenshot({path:path.join(output,id+'.png')});scenes.push({id,title});}
 const json=async url=>{const response=await page.request.get(base+'/api'+url);assert(response.ok());return response.json();};
 await page.goto(base);await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).waitFor();
 await scene('login','Acesso de demonstração');
 await page.getByRole('button',{name:'Entrar no portfólio',exact:true}).click();await page.locator('.page-fixed h1').waitFor();await ready();
 await scene('central','Emissão no centro da operação');
 const before=await json('/dashboard'),total=(await json('/invoices')).total;
 await page.getByLabel('Notas desde',{exact:true}).fill('1999-01-01');await page.getByLabel('Notas até',{exact:true}).fill('1999-01-01');
 await page.getByText('Nenhuma nota neste filtro. Sua próxima emissão aparecerá aqui.',{exact:true}).waitFor();
 const csv=await page.request.get(base+'/api/reports/invoices.csv?start=1999-01-01&end=1999-01-01');assert.equal((await csv.text()).trim().split('\n').length,1);
 await page.getByRole('button',{name:'Limpar filtros',exact:true}).click();await ready();
 await page.goto(base+'/clients');await page.locator('tbody tr').first().waitFor();assert.equal(await page.locator('tbody tr').count(),5);await scene('clientes','Clientes pessoa física e jurídica');
 await page.goto(base+'/emitir?scenario=pj');await page.getByRole('heading',{name:'Para quem você está emitindo?',exact:true}).waitFor();
 await page.waitForFunction(()=>document.querySelector('select[aria-label="Cliente / tomador"]')?.value!=='');
 assert.equal((await json('/invoices')).total,total);await scene('cliente','Escolha do tomador');
 await page.getByRole('button',{name:'Continuar',exact:true}).click();await scene('servico','Serviço, valor e competência');
 await page.getByRole('button',{name:'Revisar dados',exact:true}).click();await page.locator('.emission-checklist.validated').waitFor();await scene('revisao','Revisão antes da emissão');
 await page.getByRole('button',{name:'Emitir NFS-e simulada',exact:true}).click();await page.getByRole('heading',{name:'Documento simulado gerado',exact:true}).waitFor();await scene('resultado','Documento registrado');
 const href=await page.getByRole('link',{name:'Ver histórico fiscal',exact:true}).getAttribute('href'),id=Number(href.split('/').pop());
 const after=await json('/dashboard');assert.equal(before.expected,after.expected);assert.equal(before.received,after.received);
 const pdf=await page.request.get(base+`/api/invoices/${id}/pdf`);assert.equal(pdf.status(),200);
 fs.mkdirSync(path.resolve(__dirname,'../output/pdf'),{recursive:true});fs.writeFileSync(path.resolve(__dirname,'../output/pdf/nexofiscal-nfse-demonstracao.pdf'),await pdf.body());
 await page.goto(base+`/api/invoices/${id}/document`);await page.locator('.watermark').waitFor();await scene('documento','Documento demonstrativo com marca-d’água');
 await page.screenshot({path:path.join(output,'documento-completo.png'),fullPage:true});
 await page.goto(base+href);await page.getByRole('button',{name:'E-mail',exact:true}).click();let dialog=page.getByRole('dialog');await dialog.getByLabel('Destinatário',{exact:true}).waitFor();
 assert(await dialog.getByRole('button',{name:'Enviar e-mail',exact:true}).isDisabled());await scene('email','Entrega com PDF e permissões');
 await dialog.getByRole('tab',{name:'Avançado',exact:true}).click();const [draft]=await Promise.all([page.waitForEvent('download'),dialog.getByRole('button',{name:'Baixar mensagem (.eml)',exact:true}).click()]);
 fs.mkdirSync(path.resolve(__dirname,'../output/email'),{recursive:true});await draft.saveAs(path.resolve(__dirname,'../output/email/nexofiscal-portfolio-exemplo.eml'));
 await page.getByRole('button',{name:'Fechar janela',exact:true}).click();
 await page.goto(base+'/emitir?scenario=rejeicao');await page.getByRole('heading',{name:'Para quem você está emitindo?',exact:true}).waitFor();await page.waitForFunction(()=>document.querySelector('select[aria-label="Cliente / tomador"]')?.value!=='');
 await page.getByRole('button',{name:'Continuar',exact:true}).click();await page.getByRole('button',{name:'Revisar dados',exact:true}).click();await page.getByRole('heading',{name:'Revise antes de emitir',exact:true}).waitFor();assert(await page.getByRole('checkbox').isChecked());
 await page.getByRole('button',{name:'Emitir NFS-e simulada',exact:true}).click();await page.getByRole('heading',{name:'A simulação foi rejeitada',exact:true}).waitFor();await scene('rejeicao','Tratamento de rejeição');
 const rejectedHref=await page.getByRole('link',{name:'Ver histórico fiscal',exact:true}).getAttribute('href');await page.goto(base+rejectedHref);await page.getByRole('tab',{name:'Dados da nota',exact:true}).click();
 await page.getByRole('button',{name:'Reprocessar simulação',exact:true}).click();await page.getByRole('tab',{name:'Histórico fiscal',exact:true}).click();await page.locator('.timeline').waitFor();assert.equal((await json(rejectedHref)).attempts,2);await scene('historico','Reprocessamento com histórico');
 await page.goto(base+'/automations');await page.getByRole('heading',{name:'Automações',exact:true}).waitFor();await scene('automacoes','Rotinas locais e integração n8n');
 await page.goto(base+'/users');await page.getByRole('heading',{name:'Usuários',exact:true}).waitFor();await scene('usuarios','Acesso por perfil');
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/emitir?scenario=pf');await page.getByRole('heading',{name:'Para quem você está emitindo?',exact:true}).waitFor();await ready();
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(output,'mobile.png')});
 await page.getByRole('button',{name:'Sair',exact:true}).click();await page.getByRole('heading',{name:'Vamos começar?',exact:true}).waitFor();assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
 fs.writeFileSync(path.join(output,'scenes.json'),JSON.stringify(scenes,null,2));console.log('PASS: jornada atual, PDF, mensagem, rejeição/reprocessamento, cinco itens, filtros e mobile; nenhum e-mail enviado.');
})().catch(e=>{console.error('FAIL '+stage+' '+e.name+'; detalhes privados omitidos.');process.exitCode=1;}).finally(async()=>{await page?.unrouteAll({behavior:'ignoreErrors'});await browser?.close();});
