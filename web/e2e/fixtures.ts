import type { Page } from '@playwright/test';
export async function liveApi(page: Page, available = true) {
  const citation = {source_id:'web-test',locator:'L1',quote:'Reported revenue was 123 million.'};
  const answer = {answerable:true, answer:'Reported revenue was 123 million.', claims:[{key:'revenue',value:123,unit:'USD million',period:'FY2025',citations:[citation]}]};
  const session = {id:'test',corpus:'live-web',turns:[] as object[],workbook:null,context:null,proposals:[],exports:[]};
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if(path === '/api/auth') body={required:false,authenticated:true};
    else if(path === '/api/config') body={live_available:available,replay:false,model:'test-model',spend:{total_usd:0,cap_usd:1,remaining_usd:1},limits:{},corpora:[{id:'live-web',label:'Live web research',description:'Live sources',cutoff:'',documents:[],starters:[],workbook_starters:[],scripted:[]}]};
    else if(path.endsWith('/progress')) body={events:[],done:true,turn:session.turns[0]};
    else if(path.endsWith('/turns')) {
      const request=route.request().postDataJSON();
      session.turns=[{id:'turn-1',question:request.question,status:'completed',stop_reason:null,mode:'live_openrouter_langchain',model:'test-model',answer,metrics:null,proposal_ids:[],carried:{turns:0,workbook_range:null,snapshot_id:null},started_at:''}];
      body={turn_id:'turn-1'};
    } else if(path.includes('/sources/')) body={id:'web-test',title:'Issuer report',url:'https://example.org/report',published:'2025-12-31',total_lines:1,locator_note:'Fetched web text',has_original:false,original_type:null,lines:[{line:1,text:citation.quote,location:null}]};
    else body=session;
    await route.fulfill({json:body});
  });
}
export async function officeHost(page: Page) {
  await page.route('https://appsforoffice.microsoft.com/**', route => route.fulfill({contentType:'text/javascript',body:`
    window.Office={onReady:async()=>({host:'Excel'}),HostType:{Excel:'Excel'},context:{requirements:{isSetSupported:()=>true}}};
    window.selection={address:'Sheet1!A1',rowCount:1,columnCount:1,values:[[123]],formulas:[[123]]};
    window.Excel={run:async fn=>fn({sync:async()=>{},workbook:{getSelectedRange:()=>({load:()=>{},...window.selection}),worksheets:{add:()=>({getRangeByIndexes:()=>({set values(v){window.inserted=v},format:{}}),getRange:()=>({format:{font:{}}}),activate:()=>{}})}}})};
  `}));
}
