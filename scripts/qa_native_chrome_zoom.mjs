#!/usr/bin/env node
// Genuine Chrome tabs.setZoom via an isolated disposable MV3 extension/profile.
// Unlike CSS zoom, device emulation, or resizing, this invokes the browser's
// own page-zoom facility and reads the effective value back from Chrome.
import fs from "node:fs/promises";
import path from "node:path";
import { spawn, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const WEB=path.join(ROOT,"apps/web");
const require=createRequire(path.join(WEB,"package.json"));
const {chromium}=require("playwright");
const SITE=path.join(WEB,"out");
const HOST="http://127.0.0.1:18783";
const CHROME=chromium.executablePath();
const ZOOMS=[1,1.25,1.5,1.75,2];
const ROUTES=["/","/events/","/news/","/guide/museum/","/search/","/guide/accessible-museum/"];
const WIDTHS=[1440,1024,768];
const result={engine:"Chrome for Testing / Playwright Chromium",zoomType:"native chrome.tabs.setZoom",scaleFactors:ZOOMS,
  viewportWidths:WIDTHS,routes:ROUTES,checks:[],errors:[],start:new Date().toISOString()};

let server,context,local;
try{
 if(!await fs.stat(path.join(SITE,"index.html")).then(s=>s.isFile()).catch(()=>false))
   throw Error("Next static export missing, run npm run build");
 await fs.access(CHROME);
 try{execFileSync("lsof",["-nP","-iTCP:18783","-sTCP:LISTEN"],{stdio:"pipe"});throw Error("Port 18783 occupied: refuse to touch existing service")}catch(e){
   if(String(e.message).includes("occupied"))throw e;
 }
 local=await fs.mkdtemp(path.join(ROOT,".local_archive","native-chrome-zoom-"));
 const ext=path.join(local,"extension"),profile=path.join(local,"profile");
 await fs.mkdir(ext,{recursive:true});
 await fs.writeFile(path.join(ext,"manifest.json"),JSON.stringify({
   manifest_version:3,name:"Private local zoom QA",version:"0.0.1",
   permissions:["tabs"],host_permissions:["http://127.0.0.1:18783/*"],
   background:{service_worker:"worker.js"}
 }));
 await fs.writeFile(path.join(ext,"worker.js"),"chrome.runtime.onInstalled.addListener(()=>{});\n");
 server=spawn("python3",["-m","http.server","18783","--bind","127.0.0.1","--directory",SITE],
   {stdio:["ignore","ignore","pipe"]});
 let ready=false;
 for(let i=0;i<50;i++){
   await new Promise(r=>setTimeout(r,120));
   try{const response=await fetch(HOST);if(response.ok){ready=true;break;}}catch{}
 }
 if(!ready)throw Error("Private QA server not ready");
 context=await chromium.launchPersistentContext(profile,{
   executablePath:CHROME,headless:true,viewport:{width:1440,height:900},
   args:[`--disable-extensions-except=${ext}`,`--load-extension=${ext}`]
 });
 let worker=context.serviceWorkers()[0];
 if(!worker) worker=await context.waitForEvent("serviceworker",{timeout:15000});
 const page=await context.newPage();
 const checks=result.checks;
 for(const width of WIDTHS){
   await page.setViewportSize({width,height:900});
   for(const route of ROUTES){
     await page.goto(HOST+route,{waitUntil:"domcontentloaded"});
     const url=page.url();
     const tab=await worker.evaluate(async url=>{
       const tabs=await chrome.tabs.query({});
       return tabs.filter(t=>t.url===url).map(t=>t.id)[0]??null;
     },url);
     if(!Number.isInteger(tab))throw Error("Extension could not find target tab for "+url);
     let initialInner;
     for(const zoom of ZOOMS){
       await worker.evaluate(async({tab,zoom})=>{await chrome.tabs.setZoom(tab,zoom)},{tab,zoom});
       await page.waitForTimeout(100);
       const effective=await worker.evaluate(async tab=>chrome.tabs.getZoom(tab),tab);
       const metrics=await page.evaluate(()=>({
         innerWidth:window.innerWidth,
         clientWidth:document.documentElement.clientWidth,
         scrollWidth:document.documentElement.scrollWidth,
         bodyWidth:document.body.scrollWidth,
         dpr:devicePixelRatio,
         zoomViewport:visualViewport?.scale??1
       }));
       if(initialInner===undefined)initialInner=metrics.innerWidth;
       const overflow=Math.max(metrics.scrollWidth,metrics.bodyWidth)-metrics.clientWidth;
       const row={route,width,zoom,effective,overflow,...metrics};
       checks.push(row);
       if(Math.abs(effective-zoom)>0.005)throw Error("True tab zoom API mismatch "+JSON.stringify(row));
       if(overflow>2)throw Error("Horizontal overflow at actual page zoom "+JSON.stringify(row));
       if(zoom>1 && metrics.innerWidth>=initialInner-2)
         throw Error("Browser zoom did not actually shrink CSS viewport "+JSON.stringify(row));
     }
     await worker.evaluate(async tab=>chrome.tabs.setZoom(tab,1),tab);
   }
 }
 result.status="PASS";
 console.log("TRUE_CHROME_BROWSER_ZOOM_PASS "+checks.length+" measurements");
 console.log(JSON.stringify({sample:checks.slice(0,5),last:checks.at(-1)},null,2));
}catch(e){result.status="FAIL";result.errors.push(String(e?.stack??e));console.error("TRUE_CHROME_BROWSER_ZOOM_FAIL "+String(e));process.exitCode=1;}
finally{
 if(context)await context.close().catch(()=>{});
 if(server){server.kill("SIGTERM");}
 if(local)await fs.rm(local,{recursive:true,force:true});
 const target=path.join(ROOT,".local_archive","native-chrome-zoom-result.json");
 await fs.writeFile(target,JSON.stringify(result,null,2)+"\n");
}
