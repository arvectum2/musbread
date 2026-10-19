/** TZ-193/207: real original museum content + forms, WCAG audits.
 * Does not substitute a screen reader reading actual spoken material.
 */
import {expect,test} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {mkdirSync,writeFileSync} from "node:fs";
import path from "node:path";

test("TZ-193: official photo descriptions, archival poster and feedback forms avoid serious WCAG violations",async({page,browserName})=>{
  test.setTimeout(180_000);
  const routes=[
    "/",
    "/search/",
    "/forms/feedback/",
    "/forms/excursion/",
    "/guide/exhibitions-virtual/",
    "/news/museum-news-2025-12-30-grafik-raboty-muzeya/",
    "/guide/accessible-museum/",
  ];
  const report=[];
  for(const route of routes){
    await page.goto(route,{waitUntil:"domcontentloaded"});
    const result=await new AxeBuilder({page})
      .withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa","wcag22aa","best-practice"])
      .analyze();
    const violations=result.violations.map(v=>({
      id:v.id,impact:v.impact,description:v.description,
      nodes:v.nodes.length,samples:v.nodes.slice(0,2).map(n=>({target:n.target,summary:n.failureSummary?.slice(0,200)}))
    }));
    const blockers=violations.filter(v=>["critical","serious"].includes(v.impact??""));
    report.push({route,violations,blockers:blockers.length,incomplete:result.incomplete.length,
      passedChecks:result.passes.length});
    console.log("OFFICIAL_AXE",browserName,route,"violations",violations.length,"serious",blockers.length);
  }
  const out=path.resolve(process.cwd(),"../../.local_archive");
  mkdirSync(out,{recursive:true});
  const file=path.join(out,"tz193-axe-expanded-"+browserName+"-20261020.json");
  writeFileSync(file,JSON.stringify({browserName,report},null,2)+"\n");
  expect(report.flatMap(x=>x.violations.filter(v=>["critical","serious"].includes(v.impact??""))),
         JSON.stringify(report.filter(x=>x.blockers),null,2)).toEqual([]);
});
