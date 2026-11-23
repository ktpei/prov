import {expect,test} from '@playwright/test';
import {liveApi,officeHost} from './fixtures';
for (const width of [270,320,350]) {
  test(`Excel research fits ${width}px pane`,async({page})=>{
    await page.setViewportSize({width,height:378});
    await liveApi(page); await officeHost(page);
    await page.goto('/?excel=1');
    await expect(page.getByRole('button',{name:'Attach selected cells'})).toBeEnabled();
    await expect(page.getByRole('button',{name:'Insert cited results'})).toHaveCount(0);
    if (width === 350) await page.screenshot({path:'/tmp/provenance-pane-350.png'});
    await expect(page.getByText(/replay|demo|Cloudflare/i)).toHaveCount(0);
    await page.getByRole('button',{name:'Attach selected cells'}).click();
    await expect(page.getByRole('button',{name:'Remove selection'})).toBeVisible();
    await page.getByRole('textbox',{name:'Question',exact:true}).fill('Research revenue');
    const request=page.waitForRequest(r=>r.url().endsWith('/turns'));
    await page.getByRole('button',{name:'Ask',exact:true}).click();
    expect((await request).postDataJSON()).toMatchObject({mode:'live'});
    await expect(page.getByText('Cited answer', {exact:true})).toBeVisible();
    await page.getByText('Cited answer', {exact:true}).scrollIntoViewIfNeeded();
    await page.screenshot({path:`/tmp/provenance-result-${width}.png`});
    await page.getByRole('button',{name:'Insert cited results'}).click();
    await expect(page.getByText('Cited results inserted into a new worksheet.')).toBeVisible();
    expect(await page.evaluate(()=> (window as unknown as {inserted:unknown[][]}).inserted[1][1])).toBe(123);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.getByRole('button',{name:/Open source/}).first().click();
    await expect(page.getByRole('tab',{name:'Evidence',exact:true})).toBeVisible();
    await expect(page.getByRole('tab',{name:'Workbook',exact:true})).toHaveCount(0);
    await page.getByRole('tab',{name:'Evidence',exact:true}).click();
    await expect(page.locator('mark.quote')).toContainText('Reported revenue');
    await page.screenshot({path:`/tmp/provenance-details-${width}.png`});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.getByRole('button',{name:'Research',exact:true}).click();
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
