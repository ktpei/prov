import { expect, test } from '@playwright/test';

test('Excel selection and cited worksheet insertion', async ({ page }) => {
  await page.route('https://appsforoffice.microsoft.com/**', route => route.fulfill({
    contentType: 'text/javascript', body: `
      window.Office = { onReady: async () => ({host:'Excel'}), HostType:{Excel:'Excel'}, context:{requirements:{isSetSupported:()=>true}} };
      window.Excel = { run: async fn => fn({sync:async()=>{}, workbook:{
        getSelectedRange:()=>({load:()=>{},address:'Model!A1',rowCount:1,columnCount:1,values:[[123]],formulas:[[123]]}),
        worksheets:{add:()=>({getRangeByIndexes:()=>({set values(v){window.inserted=v},format:{}}),getRange:()=>({format:{font:{}}}),activate:()=>{}})}
      }})};`
  }));
  await page.goto('/?excel=1');
  await expect(page.getByText('Excel connected')).toBeVisible();
  await page.getByRole('button', {name:'Attach selected cells'}).click();
  await expect(page.getByText(/Selection attached/)).toBeVisible();
  await page.getByRole('button', {name:'Remove selection'}).click();
  await page.getByRole('button', {name: 'What revenue did Cloudflare report for Q3 2024, and what full-year 2024 revenue guidance did management give?'}).click();
  await expect(page.getByRole('button', {name:'Insert cited results'})).toBeEnabled();
  await page.getByRole('button', {name:'Insert cited results'}).click();
  await expect(page.getByText('Cited results inserted into a new worksheet.')).toBeVisible();
  const rows = await page.evaluate(() => (window as unknown as {inserted: unknown[][]}).inserted);
  expect(rows[0]).toEqual(['Claim', 'Value', 'Unit', 'Period', 'Evidence']);
  expect(rows.length).toBeGreaterThan(1);
  expect(String(rows[1][4])).toContain('release');
});

test('outside Excel gives actionable status', async ({page}) => {
  await page.route('https://appsforoffice.microsoft.com/**', route => route.fulfill({contentType:'text/javascript', body:''}));
  await page.goto('/?excel=1');
  await expect(page.getByText('Office.js did not load. Reopen the add-in in Excel.')).toBeVisible();
  await expect(page.getByRole('button', {name:'Attach selected cells'})).toBeDisabled();
});
