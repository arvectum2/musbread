import {test,expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for(const route of ["/","/guide/museum-contacts/","/guide/accessible-museum/","/search/"]){
 test(`TZ-117: automated WCAG 2.1 A/AA check of ${route} in large-print mode`,async({page})=>{
  await page.goto(route,{waitUntil:"networkidle"});
  await page.getByRole("button",{name:"Для слабовидящих"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
  const results=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]).analyze();
  const problems=results.violations.filter(v=>v.impact==="critical"||v.impact==="serious");
  expect(problems,problems.map(v=>`${v.id} ${v.nodes.map(n=>n.target.join(",")).join(";")}`).join("\n")).toEqual([]);
 });
}
