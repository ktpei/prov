import {expect,test} from '@playwright/test';
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
