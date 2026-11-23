import type { Page } from '@playwright/test';
import type { Session } from '../src/types';
export async function liveApi(page: Page, available = true, propose = false) {
  const citation = {source_id:'web-test',locator:'L1',quote:'Reported revenue was 123 million.'};
  const answer = {answerable:true, answer:'Reported revenue was 123 million.', claims:[{key:'revenue',value:123,unit:'USD million',period:'FY2025',citations:[citation]}]};
  const session: Session = {id:'test',corpus:'live-web',turns:[],workbook:null,context:null,proposals:[],exports:[]};
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if(path === '/api/auth') body={required:false,authenticated:true};
    else if(path === '/api/config') body={live_available:available,replay:false,model:'test-model',spend:{total_usd:0,cap_usd:1,remaining_usd:1},limits:{},corpora:[{id:'live-web',label:'Live web research',description:'Live sources',cutoff:'',documents:[],starters:[],workbook_starters:[],scripted:[]}]};
    else if(path.endsWith('/workbook') && route.request().method() === 'POST') {
      session.workbook={snapshot_id:'snap-1',sha256:'test',filename:'Excel-workbook.xlsx',sheets:[{name:'Sheet1',max_row:10,max_col:10}],warnings:[],export_blockers:[]};
      body=session.workbook;
    } else if(path.endsWith('/context')) {
      session.context=route.request().method()==='DELETE'?null:route.request().postDataJSON();
      body=session.context;
    } else if(path.endsWith('/excel/apply-plan')) {
      body={snapshot_id:'snap-1',edits:[{id:'p1',sheet:'Sheet1',cell:'A1',old_content:123,new_content:456}]};
    } else if(path.endsWith('/excel/applied')) {
      session.proposals.forEach(p=>p.status='applied'); body={ok:true};
    }
    else if(path.endsWith('/progress')) body={events:[],done:true,turn:session.turns[0]};
    else if(path.endsWith('/turns')) {
      const request=route.request().postDataJSON();
      session.turns=[{id:'turn-1',question:request.question,status:'completed',stop_reason:null,mode:'live_openrouter_langchain',model:'test-model',answer,metrics:null,proposal_ids:[],carried:{turns:0,workbook_range:null,snapshot_id:null},started_at:''}];
      if(propose) {
        session.proposals=[{id:'p1',turn_id:'turn-1',snapshot_id:'snap-1',sheet:'Sheet1',cell:'A1',old_display:'123',old_formula:null,new_content:456,rationale:'Requested input update',citations:[citation],mode:'live',model:'test-model',generated_by:'test',turn_status:'completed',status:'pending'}];
        session.turns[0].proposal_ids=['p1'];
      }
      body={turn_id:'turn-1'};
    } else if(path.includes('/sources/')) body={id:'web-test',title:'Issuer report',url:'https://example.org/report',published:'2025-12-31',total_lines:1,locator_note:'Fetched web text',has_original:false,original_type:null,lines:[{line:1,text:citation.quote,location:null}]};
    else body=session;
    await route.fulfill({json:body});
  });
}
export async function officeHost(page: Page) {
  await page.route('https://appsforoffice.microsoft.com/**', route => route.fulfill({contentType:'text/javascript',body:`
    window.fileClosed=0;
    window.Office={onReady:async()=>({host:'Excel'}),HostType:{Excel:'Excel'},FileType:{Compressed:'compressed'},AsyncResultStatus:{Succeeded:'succeeded'},context:{requirements:{isSetSupported:()=>true},document:{getFileAsync:(type,opts,cb)=>{
      if(window.captureFails) return cb({status:'failed',error:{message:'Snapshot failed'}});
      cb({status:'succeeded',value:{size:3,sliceCount:1,getSliceAsync:(i,done)=>done({status:'succeeded',value:{data:[1,2,3]}}),closeAsync:done=>{window.fileClosed++;done({status:'succeeded'});}}});
    }}}};
    window.selection={address:'Sheet1!A1',rowCount:1,columnCount:1,values:[[123]],formulas:[[123]]};
    window.liveValue=123; window.liveFormula=123; window.writeCount=0;
    const sheet={name:'Sheet1',id:'sheet-1',visibility:'Visible',load:()=>{},protection:{protected:false,load:()=>{}},
      getRange:()=>({load:()=>{},rowCount:1,columnCount:1,rowHidden:!!window.rowHidden,columnHidden:!!window.columnHidden,
        valueTypes:[[window.cellError?'Error':'Double']],
        get values(){return [[window.liveValue]]},set values(v){window.liveValue=v[0][0];window.liveFormula=v[0][0];window.writeCount++},
        get formulas(){return [[window.liveFormula]]},
        getMergedAreasOrNullObject:()=>({isNullObject:!window.isMerged}),
        getSpillParentOrNullObject:()=>({isNullObject:!window.isSpill}),
        getTables:()=>({load:()=>{},items:window.inTable?[{}]:[]})
      })};
    window.mockSheet=sheet;
    window.Excel={RangeValueType:{error:'Error'},SheetVisibility:{visible:'Visible'},CalculationType:{full:'Full'},run:async fn=>fn({sync:async()=>{},workbook:{
      application:{calculate:()=>{window.calculated=true}},
      getSelectedRange:()=>({load:()=>{},...window.selection}),worksheets:{load:()=>{},items:[sheet],getItem:()=>sheet,
      add:()=>({getRangeByIndexes:()=>({set values(v){window.inserted=v},format:{}}),getRange:()=>({format:{font:{}}}),activate:()=>{}})}
    }})};
  `}));
}
