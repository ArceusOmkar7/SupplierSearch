import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Known-supplier journey on actual records. The harness (backend/tests/acceptance/test_us1_real_run.py)
 * starts the API and worker, supplies the buyer credential and the supplier details taken from the
 * actual BIS IS 9473 licence list. Website domains come from the contact email printed in that
 * official record; they are unverified buyer-supplied identifiers.
 */
interface SupplierInput { name: string; website: string; licence: string; address: string }
const suppliers: SupplierInput[] = JSON.parse(process.env.E2E_SUPPLIERS ?? '[]');
const username = process.env.E2E_USERNAME ?? '';
const password = process.env.E2E_PASSWORD ?? '';
const outDir = process.env.E2E_OUTPUT ?? resolve(process.cwd(), '../.local/acceptance/core002/us1');
const requirement = 'Class FFP2 respirator masks conforming to IS 9473:2002';

test('buyer confirms requirements and checklist, then verification runs without buyer scraping', async ({ page }) => {
  test.skip(suppliers.length === 0 || !username, 'Run through the acceptance harness');
  test.setTimeout(25 * 60 * 1000);
  mkdirSync(outDir, { recursive: true });
  const log: string[] = [];
  page.on('dialog', dialog => { log.push(`dialog:${dialog.message()}`); void dialog.dismiss(); });

  await page.goto('/');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Your cases' })).toBeVisible();
  await expect(page.getByText('You have no cases yet')).toBeVisible();

  // Intake: the interpretation never confirms anything by itself.
  await page.getByLabel('Case title').fill('Actual BIS licence-list suppliers');
  await page.getByLabel('What do you need?').fill(requirement);
  await page.getByLabel(/Suppliers, one per line/).fill(suppliers.map(s => s.name).join('\n'));
  await page.getByRole('button', { name: 'Create case' }).click();
  await expect(page.getByRole('heading', { name: /Requirements/ })).toContainText('Draft');
  await expect(page.getByLabel(/Part or equipment/)).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Confirm requirements' })).toBeDisabled();

  // The buyer corrects everything explicitly.
  await page.getByLabel(/Part or equipment/).fill(requirement);
  await page.getByLabel(/Required certifications/).fill('IS 9473');
  await page.getByLabel(/^Standards/).fill('IS 9473');
  await page.getByLabel(/Country code/).fill('IN');
  for (const [index, supplier] of suppliers.entries()) {
    const n = index + 1;
    await page.getByRole('button', { name: `Add an identifier to supplier ${n}`, exact: true }).click();
    await page.getByLabel(`Supplier ${n} identifier value 2`).fill(supplier.website);
    await page.getByRole('button', { name: `Add an identifier to supplier ${n}`, exact: true }).click();
    await page.getByLabel(`Supplier ${n} identifier type 3`).selectOption('licence_number');
    await page.getByLabel(`Supplier ${n} identifier value 3`).fill(supplier.licence);
    await page.locator(`#address-${index}`).fill(supplier.address);
    await page.locator(`#role-${index}`).selectOption('production_site');
  }
  await page.getByRole('button', { name: 'Save draft' }).click();
  await expect(page.getByRole('button', { name: 'Confirm requirements' })).toBeEnabled();
  await page.getByRole('button', { name: 'Confirm requirements' }).click();
  await expect(page.getByRole('heading', { name: /Requirements/ })).toContainText('Confirmed');

  // Claims are proposed only after confirmation; at least one must be marked required.
  await page.getByRole('button', { name: 'Propose claims to verify' }).click();
  await expect(page.getByRole('heading', { name: /Claims to verify/ })).toBeVisible();
  const confirmChecklist = page.getByRole('button', { name: 'Confirm checklist' });
  await expect(confirmChecklist).toBeDisabled();
  for (const supplier of suppliers) {
    const group = page.getByRole('region', { name: new RegExp(supplier.name.split(/[ ,(]/)[0], 'i') }).first();
    await group.getByRole('checkbox', { name: /Legal existence/ }).check();
    await group.getByRole('checkbox', { name: /^Regulatory compliance/ }).first().check();
  }
  await expect(confirmChecklist).toBeEnabled();
  await confirmChecklist.click();
  await expect(page.getByRole('heading', { name: /Claims to verify/ })).toContainText('Confirmed');

  // Collection starts only now, and runs unattended.
  const startedAt = Date.now();
  await page.getByRole('button', { name: 'Start verification' }).click();
  await expect(page.getByRole('heading', { name: 'Verification progress' })).toBeVisible();
  await expect(page.getByText(/You do not need to visit any website or solve any CAPTCHA/)).toBeVisible();
  await expect(page.getByText(/All checks finished|Some sources gave no evidence/)).toBeVisible({ timeout: 20 * 60 * 1000 });
  const collectionSeconds = Math.round((Date.now() - startedAt) / 1000);

  // Per-supplier check tables plus the evidence matrix are rendered; the assessment is explicit.
  await expect(page.getByRole('heading', { name: 'Shortlist' })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole('heading', { name: 'Evidence by supplier and claim' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Qualified' })).toContainText('No supplier is qualified');
  const checkTables = page.locator('section[aria-label$="checks"] table');
  await expect(checkTables).toHaveCount(suppliers.length);
  const text = (await page.locator('main').innerText());
  expect(text).not.toMatch(/solve the captcha|log in to the portal|please visit/i);
  expect(text).toContain('nothing was sent');
  expect(log.filter(entry => entry.startsWith('dialog:'))).toEqual([]);
  await page.screenshot({ path: resolve(outDir, 'us1-final.png'), fullPage: true });
  writeFileSync(resolve(outDir, 'us1-ui-result.json'), JSON.stringify({
    collection_seconds: collectionSeconds, suppliers: suppliers.length, page_text: text,
  }, null, 2));
});
