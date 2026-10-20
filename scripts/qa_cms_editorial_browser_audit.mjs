/** Browser QA through disposable localhost Nginx with a synthetic MoonShine admin.
 * Do not record passwords, session cookies or user-supplied content.
 */
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';

const root=join(fileURLToPath(new URL('..',import.meta.url)));
const require=createRequire(join(root,'apps/web/package.json'));
const {chromium,webkit}=require('playwright');
const AxeBuilder=require('@axe-core/playwright').default;

const base=process.env.MUSBREAD_QA_BASE_URL;
const email=process.env.MUSBREAD_QA_EMAIL;
const password=process.env.MUSBREAD_QA_PASS;
const entry=process.env.MUSBREAD_QA_ENTRY;
if (!base || !/^http:\/\/127\.0\.0\.1:\d+$/.test(base) ||
    !email?.endsWith('@example.invalid') || !password ||
    !/^[1-9]\d*$/.test(entry ?? ''))
  throw Error('Refused unsafe browser QA environment');

const pages=[
 ['editor','/admin/resource/museum-entry-resource/museum-entry-form-page/'+entry],
 ['media','/admin/museum-media?entry='+entry],
 ['documents','/admin/museum-documents?entry='+entry],
 ['preview','/admin/museum-entries/'+entry+'/preview'],
 ['preflight','/admin/museum-content/preflight'],
];
const findings=[];
for (const [engineName,engine] of [['chromium',chromium],['webkit',webkit]]) {
  const browser=await engine.launch({headless:true});
  try {
    for (const width of [320,390,768]) {
      const context=await browser.newContext({viewport:{width,height:780}});
      try {
        const page=await context.newPage();
        await page.goto(base+'/admin/login',{waitUntil:'domcontentloaded'});
        await page.locator('input[name="username"]').fill(email);
        await page.locator('input[name="password"]').fill(password);
        await Promise.all([
          page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:16000}),
          page.locator('button[type="submit"]').first().click(),
        ]);
        for (const [name,path] of pages) {
          const response=await page.goto(base+path,{waitUntil:'domcontentloaded'});
          assert.equal(response.status(),200,engineName+' '+width+' '+name+' HTTP');
          const layout=await page.evaluate(()=>{
            const viewport=document.documentElement.clientWidth;
            const content=document.documentElement.scrollWidth;
            const culprits=Array.from(document.querySelectorAll('body *')).filter(el=>{
              const rect=el.getBoundingClientRect();
              const css=getComputedStyle(el);
              return css.visibility!=='hidden' && css.display!=='none' &&
                rect.width>0 && (rect.right>viewport+5 || rect.left<-5);
            }).slice(0,8).map(el=>({
              tag:el.tagName,cls:String(el.className).slice(0,55),
              width:Math.round(el.getBoundingClientRect().width)
            }));
            return {viewport,content,culprits};
          });
          const horizontalPan=await page.evaluate(()=>{
            const oldX=window.scrollX;
            window.scrollTo(999,0);
            const pan=window.scrollX;
            window.scrollTo(oldX,0);
            return pan;
          });
          if (name==='documents' && width<=390) {
            const region=page.getByRole('region',{name:'Таблица загруженных документов'});
            await region.focus();
            const dimensions=await region.evaluate(el=>({
              scroll:el.scrollWidth,visible:el.clientWidth
            }));
            assert.ok(dimensions.scroll>dimensions.visible,
              'Documents table must remain keyboard-scrollable inside its own region');
            await page.keyboard.press('ArrowRight');
          }
          if (name==='editor' && width===320) {
            const burger=page.locator('.btn-burger:visible').first();
            assert.ok(await burger.count()>0,'Mobile menu button should be present');
            assert.ok(await burger.getAttribute('aria-label'),'Mobile menu accessible name');
            const original=await burger.getAttribute('aria-expanded');
            await burger.focus();
            await page.keyboard.press('Enter');
            await page.waitForTimeout(80);
            const expanded=await burger.getAttribute('aria-expanded');
            assert.notEqual(expanded,original,'Enter should toggle mobile menu');
            await page.keyboard.press('Enter');
          }
          const axe=await new AxeBuilder({page}).withTags(
            ['wcag2a','wcag2aa','wcag21a','wcag21aa']
          ).analyze();
          const keyboard=await page.evaluate(()=>{
            const focusables=Array.from(document.querySelectorAll(
              'a[href],button:not([disabled]),input:not([type=hidden]),select,textarea,[tabindex]:not([tabindex="-1"])'
            )).filter(el=>el.getBoundingClientRect().width>0);
            const unnamed=focusables.filter(el=>!el.getAttribute('aria-label') &&
              !el.getAttribute('aria-labelledby') && !el.labels?.length &&
              !el.textContent.trim() && !el.getAttribute('title')).map(el=>el.outerHTML.slice(0,100));
            return {focusable:focusables.length,unnamed:unnamed.slice(0,5)};
          });
          await page.keyboard.press('Tab');
          const focusAfter=await page.evaluate(()=>({
            tag:document.activeElement?.tagName,
            visible:document.activeElement ? getComputedStyle(document.activeElement).visibility : ''
          }));
          findings.push({engine:engineName,width,page:name,
            overflow_px:layout.content-layout.viewport,
            horizontal_pan_px:horizontalPan,
            overflow_elements:layout.content>layout.viewport+4?layout.culprits:[],
            axe_violations:axe.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length,
              targets:v.nodes.slice(0,4).map(node=>({target:node.target,
                message:node.failureSummary?.slice(0,180),
                html:node.html?.slice(0,380)}))})),
            keyboard,focusAfter});
          console.log('CMS_UX_CHECK',engineName,width,name,
            'OVERFLOW',layout.content-layout.viewport,
            'AXE',axe.violations.map(x=>x.id+'('+x.nodes.length+')').join(',')||'NONE',
            'FOCUS',keyboard.focusable,focusAfter.tag);
        }
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
}
writeFileSync(join(root,'.local_archive/cms-editorial-ux-audit-20261020.json'),
  JSON.stringify({scope:'synthetic localhost authenticated CMS',checks:findings.length,findings},null,2)+'\n');
const overflow=findings.filter(f=>f.overflow_px>4);
const axe=findings.filter(f=>f.axe_violations.length);
const pan=findings.filter(f=>f.horizontal_pan_px>4);
const noFocus=findings.filter(f=>f.keyboard.focusable&&!f.focusAfter.tag);
console.log('CMS_UX_SUMMARY',JSON.stringify({
 checks:findings.length,overflow:overflow.length,pan:pan.length,axe:axe.length,noFocus:noFocus.length,
 overflow_pages:overflow.map(f=>f.engine+'/'+f.width+'/'+f.page+':'+f.overflow_px),
 axe_pages:axe.map(f=>f.engine+'/'+f.width+'/'+f.page+':'+f.axe_violations.map(v=>v.id))
}));
if (process.env.MUSBREAD_QA_ENFORCE==='1') {
  // Raw CSS scrollWidth may include a transformed, closed vendor sidebar.
  // User-visible horizontal scrolling is measured independently.
  assert.equal(pan.length,0,'Page is horizontally pannable');
  assert.equal(axe.length,0,'WCAG axe-core violations');
  assert.equal(noFocus.length,0,'Keyboard focus missing');
}
