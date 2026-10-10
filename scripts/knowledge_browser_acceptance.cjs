// Local acceptance only: creates conversations and uploads a synthetic CSV.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs');
const out=(process.env.KNOWLEDGE_EVIDENCE_DIR || 'tmp/knowledge-browser')+'/';
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const account={email:process.env.KNOWLEDGE_TEST_EMAIL,password:process.env.KNOWLEDGE_TEST_PASSWORD};
 if(!account.email || !account.password) throw Error('Provide credentials for an isolated local test account via KNOWLEDGE_TEST_EMAIL/PASSWORD.');
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const report={scope:'Real Edge UI, live API/worker/model and persisted messages; isolated test account.',runs:[],errors};
 const save=()=>fs.writeFileSync(out+'browser-e2e.json',JSON.stringify(report,null,2));
 try{
 await page.goto('http://localhost:8080');
 await page.locator('#auth-email').fill(account.email);await page.locator('#auth-password').fill(account.password);await page.locator('button[type="submit"]').click();await page.locator('.chat-input').waitFor();
 for(const mode of ['method','data']){
  await page.getByRole('button',{name:'新对话',exact:true}).last().click();
  if(mode==='data'){
   await page.locator('.chat-upload-btn').click();
   const upload=page.waitForResponse(r=>r.url().includes('/datasources/upload')&&r.request().method()==='POST',{timeout:120000});
   await page.locator('input[type=file]').setInputFiles({name:'knowledge_ctr_validation.csv',mimeType:'text/csv',buffer:Buffer.from('period,user_id,clicks,impressions\nbefore,u,2,5\nbefore,v,4,10\nafter,u,3,5\nafter,v,6,40\n')});
   const response=await upload;console.log('upload',response.status());
   if(!response.ok())throw Error('Upload failed '+response.status());
   await page.locator('.chat-datasource-modal-close').click();
  }
  const question=mode==='method'?'只讨论方法，不执行分析：三个功能实验收益分别为2%、3%、4%，季度收益可以相加报9%吗？请在200字内说明前提和参考来源。':'请执行附加CSV的CTR描述性分析。每行是一位用户一期的汇总，曝光为正；分别按period计算总点击、总曝光、总体CTR、平均用户CTR。只报告两期的结果、口径差异和参考来源，不推断因果或收入。无需报告文件或图表。';
  await page.locator('.chat-input').fill(question);
  const started=page.waitForResponse(r=>r.url().endsWith('/api/v1/chat')&&r.request().method()==='POST',{timeout:120000});
  await page.locator('.chat-send-btn').click();const response=await started;const startedBody=await response.json();
  const run={mode,question,session_id:startedBody.session_id,http_status:response.status()};report.runs.push(run);save();console.log('started',mode,run.session_id);
  for(let i=0;i<72;i++){
   await page.waitForTimeout(5000);
   const r=await page.request.get('http://localhost:8080/api/v1/sessions/'+run.session_id+'/messages');
   const body=await r.json();const messages=body.messages||[];
   if(messages.some(m=>m.role==='assistant'&&m.content)){
    run.messages=messages;run.ui_text=(await page.locator('.chat-container').innerText()).slice(-18000);run.persisted=true;save();break;
   }
   if(i%6===0)console.log('waiting',mode,i*5);
  }
  await page.screenshot({path:out+'browser-'+mode+'.png'});
  if(!run.persisted){run.timeout=true;save();throw Error(mode+' timeout');}
  await page.reload();await page.waitForTimeout(2500);
  await page.locator('.session-item').filter({hasText:question.slice(0,18)}).first().click();
  await page.locator('.message-bubble.assistant').waitFor();
  run.after_reload_text=await page.locator('.chat-container').innerText();
  const assistant=run.messages.filter(m=>m.role==='assistant').at(-1);
  const trace=assistant.steps?.find(s=>s.name==='analysis_knowledge');
  run.source_check=!!trace && JSON.parse(trace.output).matches.some(m=>m.id===(mode==='method'?'C07':'C02'));
  run.restored=run.after_reload_text.includes(mode==='method'?'C07':'C02');
  if(!run.source_check || !run.restored)throw Error('Source or history restoration check failed');
  if(mode==='data'){
   const step=assistant.steps.find(s=>s.name==='workflow_agent');
   const output=JSON.parse(step.output);
   const outputs=output.workspace_state.run.result.outputs;
   const rows=Object.values(outputs).flatMap(o=>o.dataset_ref?.preview_rows||[]).filter(r=>r.overall_ctr!==undefined);
   run.numeric_check=rows.length===2 && rows.some(r=>r.period==='before'&&(r.total_clicks??r.clicks)===6&&(r.total_impressions??r.impressions)===15&&r.overall_ctr===0.4&&r.mean_user_ctr===0.4) && rows.some(r=>r.period==='after'&&(r.total_clicks??r.clicks)===9&&(r.total_impressions??r.impressions)===45&&r.overall_ctr===0.2&&r.mean_user_ctr===0.375);
   if(!run.numeric_check)throw Error('Computed workflow rows differ from expected fixture');
  }
  await page.screenshot({path:out+'browser-'+mode+'-restored.png'});
  save();console.log('completed',mode);
 }
 }catch(e){report.failure=String(e);process.exitCode=1;save();await page.screenshot({path:out+'browser-failure.png'});console.log(report.failure);}
 finally{await browser.close();}
})();



