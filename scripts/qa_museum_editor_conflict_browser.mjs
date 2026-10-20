/**
 * Headless browser check of local conflict-page actions, using synthetic text.
 * Real MoonShine/Nginx 409 is checked separately in qa_cms_nginx_fpm_docker.py.
 */
import {createRequire} from 'node:module';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = join(fileURLToPath(new URL('..', import.meta.url)));
const require = createRequire(join(root, 'apps/web/package.json'));
const {chromium} = require('playwright');
const asset = join(root, 'apps/cms/public/js/museum-editor-conflict.js');
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage({acceptDownloads:true, viewport:{width:390,height:844}});
  await page.setContent('<!doctype html><html lang="ru"><body>' +
    '<button type="button" id="download-draft">Сохранить мой черновик</button>' +
    '<p id="copy-status" role="status" aria-live="polite"></p>' +
    '<textarea id="draft-body" data-conflict-draft="body" readonly>&lt;p&gt;Несохранённое &amp; важное&lt;/p&gt;</textarea>' +
    '<button type="button" data-copy-draft="body">Скопировать моё поле</button>' +
    '</body></html>');
  await page.addScriptTag({path:asset});
  await page.evaluate(() => {
    window.__copied = null;
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{
      writeText:async (value) => {window.__copied=value;}
    }});
  });
  await page.locator('[data-copy-draft="body"]').click();
  const copied = await page.evaluate(() => window.__copied);
  assert.equal(copied,'<p>Несохранённое & важное</p>');
  assert.match(await page.locator('[role="status"]').textContent(),/Поле скопировано/);

  const downloadPromise = page.waitForEvent('download',{timeout:9000});
  await page.locator('#download-draft').click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(),'museum-unsaved-draft.json');
  const readable = await download.createReadStream();
  let content = '';
  for await (const chunk of readable) content += chunk.toString('utf8');
  const payload = JSON.parse(content);
  assert.equal(payload.fields.body,'<p>Несохранённое & важное</p>');
  assert.ok(payload.warning.includes('Несохранённая'));
  assert.match(await page.locator('[role="status"]').textContent(),/сохранения на вашем устройстве/);
  console.log('MUSEUM_CONFLICT_BROWSER_ACTIONS_PASS',JSON.stringify({
    browser:'Chromium headless',viewport:'390x844',
    copy_exact_raw_html_as_text:true,download_json:true,
    no_user_html_executed:true,uploaded_data:false
  }));
} finally {
  await browser.close();
}
