import {expect,test} from '@playwright/test';
import {liveApi,officeHost} from './fixtures';
for (const width of [270,320,350]) {
  test(`Excel research fits ${width}px pane`,async({page})=>{
    await page.setViewportSize({width,height:378});
    await liveApi(page); await officeHost(page);
    await page.goto('/?excel=1');
    await expect(page.getByRole('button',{name:'Attach selected cells'})).toBeEnabled();
    if (width === 350) await page.screenshot({path:'/tmp/provenance-pane-350.png'});
    await expect(page.getByText(/replay|demo|Cloudflare/i)).toHaveCount(0);
    await page.getByRole('button',{name:'Attach selected cells'}).click();
    await expect(page.getByRole('button',{name:'Remove selection'})).toBeVisible();
    await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
    const request=page.waitForRequest(r=>r.url().endsWith('/turns'));
    await page.getByRole('button',{name:'Ask',exact:true}).click();
    expect((await request).postDataJSON()).toMatchObject({mode:'live'});
    await expect(page.getByText('Cited answer', {exact:true})).toBeVisible();
    await page.getByText('Cited answer',{exact:true}).scrollIntoViewIfNeeded();
    await page.screenshot({path:`/tmp/provenance-new-answer-${width}.png`});
    await page.getByRole('button',{name:'Insert cited results'}).click();
    await expect(page.getByText('Cited results inserted into a new worksheet.')).toBeVisible();
    expect(await page.evaluate(()=> (window as unknown as {inserted:unknown[][]}).inserted[1][1])).toBe(123);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.getByRole('button',{name:/Open source/}).first().click();
    await expect(page.locator('mark.quote')).toContainText('Reported revenue');
    await page.screenshot({path:`/tmp/provenance-new-evidence-${width}.png`});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.getByRole('button',{name:'Back to research',exact:true}).click();
    await expect(page.getByRole('textbox',{name:'Question',exact:true})).toBeVisible();
  });
}
test('Office missing shows connection error',async({page})=>{
  await liveApi(page);
  await page.route('https://appsforoffice.microsoft.com/**',r=>r.fulfill({body:'',contentType:'text/javascript'}));
  await page.goto('/?excel=1');
  await expect(page.getByText('Office.js did not load. Reopen the add-in in Excel.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Attach selected cells'})).toBeDisabled();
});

test('Excel full-height welcome and original web reference', async ({page}) => {
  await liveApi(page); await officeHost(page);
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/');
  await expect(page.getByRole('textbox',{name:'Question',exact:true})).toBeVisible();
  await page.screenshot({path:'/tmp/provenance-web-reference.png'});
  await page.setViewportSize({width:350,height:760});
  await page.goto('/?excel=1');
  await expect(page.getByRole('button',{name:'Attach selected cells'})).toBeEnabled();
  await page.screenshot({path:'/tmp/provenance-new-welcome.png'});
  await page.getByRole('button',{name:'Attach selected cells'}).click();
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('What was reported revenue in FY2025?');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(page.getByText('Cited answer',{exact:true})).toBeVisible();
  await expect(page.getByText('Attached Excel cells',{exact:true})).toBeVisible();
  await page.screenshot({path:'/tmp/provenance-new-answer-full.png'});
  await page.getByText('Attached Excel cells',{exact:true}).click();
  await expect(page.locator('pre')).toContainText('Sheet1!A1');
});

test('attached cells are explicit snapshots that can be updated and removed', async ({page}) => {
  await liveApi(page); await officeHost(page);
  await page.setViewportSize({width:350,height:760});
  await page.goto('/?excel=1');
  await page.getByRole('button',{name:'Attach selected cells'}).click();
  await expect(page.getByText('Sheet1!A1',{exact:true})).toBeVisible();
  await expect(page.getByText('1 cell attached · snapshot')).toBeVisible();
  await page.getByText('Preview values',{exact:true}).click();
  await expect(page.getByRole('cell',{name:'123',exact:true})).toBeVisible();
  await page.evaluate(() => { (window as unknown as {selection:unknown}).selection = {
    address:'Forecast!B2:C2',rowCount:1,columnCount:2,values:[[456,789]],formulas:[[456,789]]
  }; });
  await expect(page.getByText('Sheet1!A1',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Update from selection'}).click();
  await expect(page.getByText('Forecast!B2:C2',{exact:true})).toBeVisible();
  await expect(page.getByText('2 cells attached · snapshot')).toBeVisible();
  await expect(page.getByRole('cell',{name:'456',exact:true})).toBeVisible();
  await page.screenshot({path:'/tmp/provenance-selection.png'});
  await page.setViewportSize({width:270,height:378});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await expect(page.getByRole('textbox',{name:'Question',exact:true})).toBeInViewport();
  await page.evaluate(() => { (window as unknown as {selection:unknown}).selection = {
    address:'Forecast!A1:A201',rowCount:201,columnCount:1,values:[],formulas:[]
  }; });
  await page.getByRole('button',{name:'Update from selection'}).click();
  await expect(page.getByText('Select at most 200 cells.')).toBeVisible();
  await expect(page.getByText('Forecast!B2:C2',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Remove selection'}).click();
  await expect(page.getByText('Forecast!B2:C2',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Attach selected cells'})).toBeEnabled();
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
  const request=page.waitForRequest(r=>r.url().endsWith('/turns'));
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  expect((await request).postDataJSON().question).toBe('Research revenue');
});

test('Excel captures workbook before asking and applies only after approval', async ({page}) => {
  await liveApi(page, true, true); await officeHost(page);
  await page.setViewportSize({width:350,height:760});
  await page.goto('/?excel=1');
  const requests: string[] = [];
  page.on('request', request => { if (request.method()==='POST') requests.push(new URL(request.url()).pathname); });
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Set the input to 456');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  const approve = page.getByRole('button',{name:'Approve 1 change in Excel'});
  await expect(approve).toBeVisible();
  expect(requests.indexOf('/api/sessions/test/workbook')).toBeLessThan(requests.indexOf('/api/sessions/test/turns'));
  expect(await page.evaluate(()=>Reflect.get(window,'fileClosed'))).toBe(1);
  expect(await page.evaluate(()=>Reflect.get(window,'writeCount'))).toBe(0);
  await approve.click();
  await expect(page.getByText('Applied in Excel',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>Reflect.get(window,'liveValue'))).toBe(456);
  expect(await page.evaluate(()=>Reflect.get(window,'calculated'))).toBe(true);
  await page.screenshot({path:'/tmp/provenance-excel-applied.png'});
});

for (const [key, value] of [['liveValue', '123'], ['liveFormula', '=A2'], ['isMerged', true], ['isSpill', true], ['inTable', true], ['cellError', true], ['rowHidden', true], ['columnHidden', true]] as const) {
  test('Excel rejects changed or unsafe target: '+key, async ({page}) => {
    await liveApi(page, true, true); await officeHost(page);
    await page.goto('/?excel=1');
    await page.getByRole('textbox',{name:'Question',exact:true}).fill('Set input to 456');
    await page.getByRole('button',{name:'Ask',exact:true}).click();
    const approve = page.getByRole('button',{name:'Approve 1 change in Excel'});
    await expect(approve).toBeVisible();
    await page.evaluate(({key,value})=>Reflect.set(window,key,value),{key,value});
    await approve.click();
    await expect(page.getByRole('alert')).toContainText(/changed since|Cannot edit/);
    expect(await page.evaluate(()=>Reflect.get(window,'writeCount'))).toBe(0);
  });
}

test('failed workbook capture stops submission and preserves question', async ({page}) => {
  await liveApi(page); await officeHost(page);
  await page.goto('/?excel=1');
  await page.evaluate(()=>Reflect.set(window,'captureFails',true));
  let submitted = false;
  page.on('request',request=>{if(request.url().endsWith('/turns'))submitted=true;});
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Change my model');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Snapshot failed');
  await expect(page.getByRole('textbox',{name:'Question',exact:true})).toHaveValue('Change my model');
  expect(submitted).toBe(false);
});

test('applied changes with failed receipt are not retried', async ({page}) => {
  await liveApi(page, true, true); await officeHost(page);
  await page.route('**/excel/applied',route=>route.fulfill({status:500,json:{detail:'Unavailable'}}));
  await page.goto('/?excel=1');
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Set input to 456');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  const approve = page.getByRole('button',{name:'Approve 1 change in Excel'});
  await approve.click();
  await expect(page.getByRole('alert')).toContainText('changes were applied and read back');
  await approve.click();
  await expect(page.getByRole('alert')).toContainText('Ask again');
  expect(await page.evaluate(()=>Reflect.get(window,'writeCount'))).toBe(1);
});
