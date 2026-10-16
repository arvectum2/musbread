#!/usr/bin/env node
// TZ-241: reproducible localhost lab timings, NOT evidence of production SLA.
// Chrome 4x CPU throttle, 150ms artificial RTT, ~1.6Mbps throughput, cold cache.
import { chromium } from '@playwright/test';
import {spawn} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
const port=19871;
const output=process.argv[2] ?? 'tz241-local-lab.json';
const server=spawn('python3',['-m','http.server',String(port),'--bind','127.0.0.1','--directory','out'],{
  stdio:'ignore',cwd:process.cwd(),detached:false,
});
const sleep=ms=>new Promise(res=>setTimeout(res,ms));
let browser;
try{
 let alive=false;
 for(let i=0;i<50;i++){
  try{const response=await fetch(`http://127.0.0.1:${port}/`);
      if(response.ok){alive=true;break;}}catch{}
  await sleep(90);
 }
 if(!alive)throw new Error('Local static server did not start');
 browser=await chromium.launch({headless:true});
 const routes=['/','/news/','/guide/museum/','/search/'];
 const samples=[];
 for(const route of routes){
  for(let round=0;round<3;round++){
   const context=await browser.newContext({viewport:{width:390,height:844}});
   const page=await context.newPage();
   await page.addInitScript(()=>{
    window.__museumLCP=null;
    try{new PerformanceObserver(list=>{
      const recent=list.getEntries().at(-1);
      if(recent)window.__museumLCP=recent.startTime;
    }).observe({type:'largest-contentful-paint', buffered:true});}catch{}
   });
   const session=await context.newCDPSession(page);
   await session.send('Network.enable');
   await session.send('Network.emulateNetworkConditions',{
    offline:false,latency:150,downloadThroughput:200_000,uploadThroughput:75_000,
   });
   await session.send('Emulation.setCPUThrottlingRate',{rate:4});
   await page.goto(`http://127.0.0.1:${port}${route}`,{waitUntil:'load',timeout:30000});
   await sleep(90);
   const timing=await page.evaluate(()=>{
    const nav=performance.getEntriesByType('navigation')[0];
    const paint=performance.getEntriesByType('paint').find(p=>p.name==='first-contentful-paint');
    return {load_ms:Math.round(nav.loadEventEnd),
      dom_content_loaded_ms:Math.round(nav.domContentLoadedEventEnd),
      first_contentful_paint_ms:paint?Math.round(paint.startTime):null,
      largest_contentful_paint_ms:window.__museumLCP?Math.round(window.__museumLCP):null,
      transfer_bytes:performance.getEntriesByType('resource').reduce((sum,r)=>sum+(r.transferSize||0),0)};
   });
   samples.push({route,round,...timing});
   await context.close();
  }
 }
 const p75=s=>s.slice().sort((a,b)=>a-b)[Math.ceil(s.length*.75)-1];
 const summary=routes.map(route=>{
   const measures=samples.filter(s=>s.route===route);
   return {route,p75_load_ms:p75(measures.map(s=>s.load_ms)),
     max_load_ms:Math.max(...measures.map(s=>s.load_ms)),
     p75_fcp_ms:p75(measures.map(s=>s.first_contentful_paint_ms??0)),
     p75_lcp_ms:p75(measures.map(s=>s.largest_contentful_paint_ms??0)),
   };
 });
 const report={kind:'local-lab-NOT-production-SLA',timestamp:new Date().toISOString(),
   network:'150ms RTT, 1.6Mbps, CPU slowdown x4; 390px mobile, cold context',
   samples,summary,all_p75_load_within_3s:summary.every(s=>s.p75_load_ms<=3000)};
 writeFileSync(resolve(output),JSON.stringify(report,null,2)+'\n',{mode:0o600});
 console.log(JSON.stringify(summary));
 console.log('TZ241_LOCAL_LAB',report.all_p75_load_within_3s?'PASS':'OVER_BUDGET','not real visitor SLA');
}finally{
 await browser?.close();
 server.kill('SIGTERM');
}
