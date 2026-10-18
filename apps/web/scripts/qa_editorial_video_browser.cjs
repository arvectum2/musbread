/* eslint-disable @typescript-eslint/no-require-imports */
const {chromium}=require('@playwright/test');
const assert=require('node:assert/strict');
(async()=>{
 const root=process.argv[2];
 if(!/^http:\/\/127\.0\.0\.1:\d+\/$/.test(root))throw new Error('Only ephemeral local QA web allowed');
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:320,height:740}});
  const external=[];
  await page.route(/https:\/\/(vk\.com|vkvideo\.ru)\//,route=>{
    external.push(route.request().url());
    return route.abort();
  });
  await page.goto(root+'museum/science-seminar-2026-04-16-633/',{waitUntil:'domcontentloaded'});
  const video=page.locator('.museum-inline-video');
  assert.equal(await video.count(),1,'Approved WYSIWYG video must appear inside actual CMS page');
  assert.match(await video.textContent(),/QA: запись научного семинара/);
  assert.equal(await video.locator('iframe').count(),0,'No passive VK iframe');
  assert.deepEqual(external,[],'No VK network before consent');
  const before=page.locator('.museum-rich-video-content .rich-text');
  assert.equal(await before.count(),2,'Video must split actual editorial article body in two parts');
  const text=await page.locator('.museum-rich-video-content').textContent();
  assert(text.indexOf('QA: часть текста до ролика')<text.indexOf('QA: запись научного семинара'),'Video respects WYSIWYG ordering');
  assert(text.indexOf('QA: часть текста после ролика')>text.indexOf('QA: запись научного семинара'),'Following paragraph appears after player');
  await video.getByRole('button',{name:'Читать текстовую альтернативу'}).click();
  assert.match(await video.getByRole('region',{name:/Текстовая альтернатива/}).textContent(),/QA: доступное текстовое описание/);
  // Install the request listener BEFORE click. iframe attachment is
  // synchronous, network navigation is asynchronous in Chromium.
  const firstVerifiedVkRequest=page.waitForRequest(
    request=>/^https:\/\/(vk\.com|vkvideo\.ru)\//.test(request.url()),
    {timeout:8000});
  await video.getByRole('button',{name:'Посмотреть видеозапись'}).click();
  assert.equal(await video.locator('iframe').count(),1);
  assert.match(await video.locator('iframe').getAttribute('src'),/^https:\/\/vk\.com\/video_ext\.php\?/);
  assert.equal(await video.locator('iframe').getAttribute('referrerpolicy'),'no-referrer');
  await page.waitForFunction(()=>document.querySelector('.museum-inline-video iframe')!==null);
  const requested=await firstVerifiedVkRequest;
  // Chromium may emit a frame navigation request which CSP blocks before
  // Playwright route interception. Do not require the route hook to see it:
  // the actual page request and safe iframe URL are the evidence of opt-in.
  assert.match(requested.url(),/^https:\/\/(vk\.com|vkvideo\.ru)\/video_ext\.php\?/,
    'Video click must initiate only the verified VK iframe navigation');
  const noOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert(noOverflow<=2,'CMS inline video overflows 320px by '+noOverflow);
  await video.getByRole('button',{name:'Закрыть видеоплеер'}).click();
  assert.equal(await video.locator('iframe').count(),0);
  await page.goto(root+'museum/science-seminar-2025-11-06-536/');
  assert.equal(await page.locator('.museum-inline-video').count(),0,'Other draft video not public');
  console.log('PASS: real isolated Laravel->Next CMS WYSIWYG approved inline video, opt-in VK privacy, text alternative, ordered paragraphs, 320px and private draft isolation');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
