const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'../..');
const exe=path.join(ROOT,'.local_archive/browser_compat_20261019/apps/Chromium-Gost.app/Contents/MacOS/Chromium-Gost');
const base='http://127.0.0.1:18088';
async function main(){
 const browser=await chromium.launch({executablePath:exe,headless:true,timeout:25000});
 const records=[];const check=(test,ok,detail='')=>records.push({test,status:ok?'PASS':'FAIL',detail:String(detail).slice(0,180)});
 try{
  check('genuine GOST version',browser.version()==='152.0.7977.149',browser.version());
  const page=await browser.newPage({viewport:{width:1366,height:850}});
  const paths=['/','/novosty/','/guide/museum-contacts/','/guide/museum-feedback/','/guide/excursion-overview/','/forms/feedback/','/forms/excursion/','/documents/','/search/'];
  for(const route of paths){
   try{const response=await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:18000});
    const title=await page.title();check('page '+route,response.status()===200&&title.length>0,response.status()+' '+title);
   }catch(e){check('page '+route,false,e.message)}
  }
  const ua=await page.evaluate(()=>navigator.userAgent);
  check('actual Chromium GOST UA',ua.includes('Chromium GOST'),ua);
  await page.goto(base+'/forms/feedback/');
  await page.getByLabel('Ваше имя').fill('Тест ГОСТ');
  await page.getByLabel('Ваш вопрос').fill('Проверка формы');
  await page.getByRole('button',{name:'Сформировать письмо'}).click();
  const href=await page.getByRole('link',{name:/Открыть письмо в почтовой программе/}).getAttribute('href');
  check('feedback form functional',href.startsWith('mailto:musbread@cult.gugov.spb.ru?'));
  for(const width of [390,768,1366]){
   await page.setViewportSize({width,height:820});
   for(const route of ['/','/novosty/','/forms/feedback/']){
    await page.goto(base+route);
    const scroll=await page.evaluate(()=>document.documentElement.scrollWidth);
    check('no horizontal overflow '+width+' '+route,scroll<=width+3,'scrollWidth='+scroll);
   }
  }
  await page.goto(base+'/guide/museum-contacts/');await page.keyboard.press('Tab');
  const focused=await page.evaluate(()=>document.activeElement?.tagName);
  check('keyboard focus',focused==='A'||focused==='BUTTON',focused);
  // All 467 original public paths: the actual GOST engine must parse the
  // museum page DOM (not merely receive a 200 from an HTTP client).
  const corpus=JSON.parse(fs.readFileSync(path.join(ROOT,'.local_archive/browser_compat_20261019/official_html_paths.json')));
  let checked=0,failed=[];
  await page.setViewportSize({width:1366,height:850});
  for(const route of corpus){
   try{
    const reply=await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:15000});
    const title=await page.title();
    if(reply?.status()!==200||title.length===0) failed.push({route,status:reply?.status(),title});
    checked++;
   }catch(e){failed.push({route,error:String(e).slice(0,90)});}
  }
  check('all original site HTML pages in actual Chromium-GOST',checked===467&&failed.length===0,
    JSON.stringify({checked,failed:failed.slice(0,3)}));
  await page.close();
 }finally{await browser.close()}
 const summary={browser:'Chromium-Gost',version:'152.0.7977.149',native_arch:'macos-arm64',isolated_local_http:true,checks:records.length,passed:records.filter(x=>x.status==='PASS').length,failed:records.filter(x=>x.status==='FAIL').length,results:records};
 fs.writeFileSync(path.join(ROOT,'docs/tz-audit/CHROMIUM_GOST_BROWSER_CHECK_20261019.json'),JSON.stringify(summary,null,2)+'\n');
 console.log(JSON.stringify({checks:summary.checks,passed:summary.passed,failed:summary.failed,failures:records.filter(x=>x.status==='FAIL')}));
 if(summary.failed)process.exitCode=1;
}
main().catch(e=>{console.error(e.stack);process.exitCode=2});
