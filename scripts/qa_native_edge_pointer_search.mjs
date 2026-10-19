/** Isolated real headful Edge: pointer-click global site search, unlike headless. */
import {chromium} from "../apps/web/node_modules/playwright/index.mjs";
import {spawn,spawnSync} from "node:child_process";
import {writeFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const url="http://127.0.0.1:19609/search/";
const exe="/Volumes/ArvectumSSD/arvectum/.tooling/browser-apps/Microsoft Edge.app/Contents/MacOS/Microsoft Edge";
function osa(code) {
  const a=spawnSync("/usr/bin/osascript",["-e",code],{encoding:"utf8",timeout:6500});
  if(a.status!==0)throw Error(String(a.stderr).slice(0,180));
  return a.stdout.trim();
}
const before=osa('tell application "System Events" to get name of every process whose frontmost is true');
if(!["Safari","Finder"].includes(before))throw Error("Foreground busy; no GUI interaction");
const web=spawn("python3",["-m","http.server","19609","--bind","127.0.0.1","--directory",root+"/apps/web/out"],{stdio:"ignore"});
let browser;
const report={kind:"real-headful-Microsoft-Edge-site-search-pointer",original:before};
try{
  for(let n=0;n<25;n++){
    try{if((await fetch(url)).ok)break;}catch{}
    await new Promise(r=>setTimeout(r,120));
  }
  browser=await chromium.launch({executablePath:exe,headless:false,timeout:18000});
  report.version=browser.version();
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const res=await page.goto(url,{waitUntil:"load",timeout:15000});
  if(res.status()!==200)throw Error("Search HTTP "+res.status());
  if(osa('tell application "System Events" to get name of every process whose frontmost is true')!=="Microsoft Edge")
    throw Error("Unexpected focus");
  await page.getByRole("combobox",{name:"Поиск по сайту"}).fill("конвейера");
  report.actualRAF=await page.evaluate(()=>Promise.race([
    new Promise(r=>requestAnimationFrame(()=>r(true))),
    new Promise(r=>setTimeout(()=>r(false),1300))
  ]));
  await page.getByRole("button",{name:/Показать все результаты/}).click({timeout:7000});
  const result=page.getByRole("region",{name:"Все результаты поиска"})
    .getByRole("link",{name:"Демонстрационная новость"});
  await result.waitFor({state:"visible",timeout:5000});
  report.target=await result.getAttribute("href");
  report.pass=report.actualRAF&&report.target==="/news/demo-news/";
  if(!report.pass)throw Error("Unexpected search result");
}finally{
  await browser?.close();
  web.kill();
  if(osa('tell application "System Events" to get name of every process whose frontmost is true')!==before)
    osa('tell application "'+before+'" to activate');
  report.restored=osa('tell application "System Events" to get name of every process whose frontmost is true');
  writeFileSync(root+"/.local_archive/tz259-native-edge-headful-pointer-20261019.json",JSON.stringify(report,null,2)+"\n");
  console.log("EDGE_HEADFUL_POINTER",JSON.stringify(report));
}
if(!report.pass)process.exitCode=1;
