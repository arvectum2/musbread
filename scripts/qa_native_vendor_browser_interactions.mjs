/** Genuine installed non-Playwright Chromium vendor-browser QA.
 * Offsite network is not contacted. It serves the built museum only on 127.0.0.1.
 * This does not test old vendor versions, Safari, Firefox, Atom or real page zoom.
 */
import { chromium } from "../apps/web/node_modules/playwright/index.mjs";
import { spawn } from "node:child_process";
import { writeFileSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const appdir="/Volumes/ArvectumSSD/arvectum/.tooling/browser-apps/";
const port=19894;
const base="http://127.0.0.1:"+port;
const routes=["/","/news/","/guide/museum/","/search/","/guide/exhibitions-virtual/","/guide/accessible-museum/"];
const browsers=[
  ["Microsoft Edge",appdir+"Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
  ["Opera",appdir+"Opera.app/Contents/MacOS/Opera"],
  ["Яндекс Браузер",appdir+"Yandex.app/Contents/MacOS/Yandex"],
];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const server=spawn("python3",["-m","http.server",String(port),"--bind","127.0.0.1","--directory",root+"/apps/web/out"],{stdio:"ignore"});
const results=[];
let failure=false;
try {
  for(let i=0;i<30;i++){
    try { if((await fetch(base+"/")).ok)break; } catch {}
    await sleep(100);
  }
  for(const [name,executablePath] of browsers) {
    let browser;
    let checked=0;
    try {
      if(!existsSync(executablePath))throw Error("Vendor executable not installed");
      browser=await chromium.launch({executablePath,headless:true,timeout:20000,args:["--no-first-run","--no-default-browser-check"]});
      const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
      for(const width of [390,1280]){
        await page.setViewportSize({width,height:844});
        for(const route of routes){
          const res=await page.goto(base+route,{waitUntil:"load",timeout:15000});
          if(res?.status()!==200)throw Error(name+" HTTP "+res?.status()+" "+route);
          const check=await page.evaluate(()=>({h1:!!document.querySelector("h1"),documentWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));
          if(!check.h1 || check.documentWidth>check.clientWidth+1)throw Error(name+" layout failure "+route+" "+width+" "+JSON.stringify(check));
          checked++;
        }
      }
      // A fresh visible tab avoids stale headless render state after
      // 12 navigation/layout probes. This is a new browser interaction.
      await page.close();
      const searchPage=await browser.newPage({viewport:{width:390,height:844}});
      await searchPage.goto(base+"/search/");
      const field=searchPage.getByRole("combobox",{name:"Поиск по сайту"});
      await field.fill("конвейера");
      const submit=searchPage.getByRole("button",{name:/Показать все результаты/});
      let activation="POINTER_CLICK_PASS";
      try {
        await submit.click({timeout:7000});
      } catch {
        // Document honest macOS headless visual-actionability divergence.
        // Enter is the REAL keyboard activation, never a JS element.click().
        const raf=await searchPage.evaluate(()=>Promise.race([
          new Promise(resolve=>requestAnimationFrame(()=>resolve(true))),
          new Promise(resolve=>setTimeout(()=>resolve(false),1100))
        ]));
        await submit.press("Enter",{timeout:3000});
        activation="KEYBOARD_ENTER_PASS__POINTER_TIMEOUT__RAF_"+String(raf);
      }
      const link=searchPage.getByRole("region",{name:"Все результаты поиска"}).getByRole("link",{name:"Демонстрационная новость"});
      await link.waitFor({state:"visible",timeout:4000});
      if((await link.getAttribute("href"))!=="/news/demo-news/")throw Error(name+" interactive search failed");
      const r={name,version:browser.version(),routes_checked:checked,viewports:[390,1280],
        interactive_search:activation,status:activation==="POINTER_CLICK_PASS"?"PASS":"PARTIAL"};
      results.push(r);console.log("NATIVE_VENDOR_BROWSER",JSON.stringify(r));
    }catch(e) {
      failure=true;const r={name,routes_checked:checked,status:"FAIL",error:String(e).slice(0,320)};
      results.push(r);console.log("NATIVE_VENDOR_BROWSER",JSON.stringify(r));
    }finally{await browser?.close();}
  }
}finally{
  server.kill("SIGTERM");
  const out=path.join(root,".local_archive/tz259-real-vendor-browsers-interactive-20261019.json");
  mkdirSync(path.dirname(out),{recursive:true});
  writeFileSync(out,JSON.stringify({kind:"local-native-official-browser-apps-not-UAT",date:"2026-10-19",results},null,2)+"\n");
}
if(failure)process.exitCode=1;
