import {expect,test,type Page} from '@playwright/test';
import {liveApi} from './fixtures';
test('live research and evidence inspection',async({page})=>{
  await liveApi(page); await page.goto('/');
  await expect(page.getByText(/demo|replay|Cloudflare/i)).toHaveCount(0);
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(page.getByText('Cited answer',{exact:true})).toBeVisible();
  await expect(page.locator('mark.quote')).toContainText('Reported revenue');
});
test('missing live configuration disables research',async({page})=>{
  await liveApi(page,false); await page.goto('/');
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
  await expect(page.getByRole('button',{name:'Ask',exact:true})).toBeDisabled();
});
async function openWorkbook(page: Page) {
  await liveApi(page); await page.goto('/');
  await page.getByRole('tab',{name:/Workbook/}).click();
  await page.getByLabel('Upload an .xlsx workbook').setInputFiles({name:'model.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from('test')});
  await page.locator('[data-cell="A1"]').click();
  await expect(page.getByText('Workbook range Sheet1!A1 attached')).toBeVisible();
}
test('workbook selection follows mouse and keyboard and can be removed',async({page})=>{
  await openWorkbook(page);
  await page.locator('[data-cell="B2"]').click({modifiers:['Shift']});
  await expect(page.getByText('Workbook range Sheet1!A1:B2 attached')).toBeVisible();
  await page.locator('[data-cell="A1"]').click();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByText('Workbook range Sheet1!B1 attached')).toBeVisible();
  await page.getByRole('tab',{name:'Evidence',exact:true}).click();
  await expect(page.getByText('Workbook range Sheet1!B1 attached')).toBeVisible();
  await page.getByRole('button',{name:/Remove/}).click();
  await expect(page.getByText('Workbook range Sheet1!B1 attached')).toHaveCount(0);
  const cleared=page.waitForRequest(r=>r.method()==='DELETE' && r.url().endsWith('/context'));
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  await cleared;
});
test('selected cell is saved before the turn starts',async({page})=>{
  await openWorkbook(page);
  let release!: () => void;
  const gate=new Promise<void>(resolve=>{release=resolve;});
  let saved=false, turnStarted=false;
  await page.route('**/context',async route=>{
    expect(route.request().postDataJSON()).toEqual({sheet:'Sheet1',range:'A1'});
    await gate; saved=true; await route.fallback();
  });
  page.on('request',r=>{
    if(r.method()==='POST' && r.url().endsWith('/turns')) { expect(saved).toBe(true); turnStarted=true; }
  });
  await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
  const saving=page.waitForRequest(r=>r.method()==='PUT' && r.url().endsWith('/context'));
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  await saving;
  expect(turnStarted).toBe(false);
  release();
  await expect(page.getByText('Cited answer',{exact:true})).toBeVisible();
  expect(turnStarted).toBe(true);
});
test('context save failure preserves the question and starts no turn',async({page})=>{
  await openWorkbook(page);
  let turns=0;
  page.on('request',r=>{ if(r.method()==='POST' && r.url().endsWith('/turns')) turns++; });
  await page.route('**/context',route=>route.fulfill({status:400,json:{detail:'Context unavailable'}}));
  const question=page.getByRole('textbox',{name:'Question',exact:true});
  await question.fill('Research revenue');
  await page.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Context unavailable');
  await expect(question).toHaveValue('Research revenue');
  expect(turns).toBe(0);
});
