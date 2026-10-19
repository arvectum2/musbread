import {chromium} from "/Volumes/ArvectumSSD/arvectum/repos/musbread/apps/web/node_modules/playwright/index.mjs";
import {spawn,spawnSync} from "node:child_process";
import {writeFileSync} from "node:fs";
const root="/Volumes/ArvectumSSD/arvectum/repos/musbread";
const browserPath="/Volumes/ArvectumSSD/arvectum/.tooling/browser-apps/Microsoft Edge.app/Contents/MacOS/Microsoft Edge";
const base="http://127.0.0.1:19597";
const routes=["/","/news/","/guide/museum/","/search/","/guide/exhibitions-virtual/","/guide/accessible-museum/"];
const widths=[1280,1024,768], levels=[100,125,150,175,200];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const osa=script=>{
  const out=spawnSync("/usr/bin/osascript",["-e",script],{encoding:"utf8",timeout:6000});
  if(out.status!==0)throw new Error("AppleScript: "+String(out.stderr).slice(0,120));
  return (out.stdout||"").trim();
};
const front=()=>osa('tell application "System Events" to get name of every process whose frontmost is true');
const key=k=>osa('tell application "System Events" to keystroke "'+k+'" using command down');
const original=front();
if(!["Safari","Finder"].includes(original))throw Error("Active app "+original+"; cannot take keyboard.");
const web=spawn("python3",["-m","http.server","19597","--bind","127.0.0.1","--directory",root+"/apps/web/out"],{stdio:"ignore"});
let browser;
let checked=[], errors=[], version="";
const measure=page=>page.evaluate(()=>({
  url:location.pathname,hasH1:!!document.querySelector("h1"),
  ratio:devicePixelRatio,cssZoom:document.body.style.zoom,
  clientWidth:document.documentElement.clientWidth,
  scrollWidth:document.documentElement.scrollWidth
}));
try{
  for(let i=0;i<40;i++){try{if((await fetch(base+"/")).ok)break;}catch{}await sleep(120);}
  browser=await chromium.launch({executablePath:browserPath,headless:false,timeout:18000});
  version=browser.version();
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  for(const width of widths){
    await page.setViewportSize({width,height:900});
    for(const route of routes){
      await page.goto(base+route,{waitUntil:"load",timeout:16000});
      if(front()!=="Microsoft Edge")throw Error("Foreground moved: keyboard test refused");
      key("0");await sleep(250);
      for(const zoom of levels){
        const goal=zoom/100;
        let m=await measure(page);
        for(let step=0;step<10&&Math.abs(m.ratio-goal)>.05;step++){
          key(m.ratio<goal?"+":"-");
          await sleep(300);
          m=await measure(page);
        }
        const pass=m.url===route&&m.hasH1&&Math.abs(m.ratio-goal)<.05&&m.cssZoom===""&&m.scrollWidth<=m.clientWidth+1;
        const rec={route,width,expectedZoom:zoom,pass,...m};
        checked.push(rec);if(!pass)errors.push(rec);
      }
      key("0");await sleep(160);
      console.log("EDGE_ZOOM",width,route,checked.length,"errors",errors.length);
    }
  }
}finally{
  await browser?.close();
  web.kill();
  if(front()!==original)osa('tell application "'+original+'" to activate');
  const report={kind:"real-GUI-Microsoft-Edge-Cmd+Plus-PageZoom",version,original,restored:front(),
    requestedCases:90,checked:checked.length,errors:errors.length,
    rows:checked,examples:errors.slice(0,8)};
  writeFileSync(root+"/.local_archive/tz238-native-edge-zoom-20261019.json",JSON.stringify(report,null,2)+"\n");
  console.log("RESULT",JSON.stringify({...report,rows:undefined}));
}
if(errors.length||checked.length!==90)process.exitCode=1;
