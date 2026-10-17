import {expect,test} from "@playwright/test";

const refs=[
 ["TZ-129","museum-history","/o-muzee"],
 ["TZ-130","building-history","/istoriya-zdaniya"],
 ["TZ-131","museum-exposition","/ekspozicii"],
 ["TZ-141","tickets-and-benefits","/stoimost"],
 ["TZ-144","accessible-museum","/informaciya-dlya-mgn"],
 ["TZ-156","excursion-interactive","/interaktivnye-zanyatiya"],
 ["TZ-157","excursion-thematic","/tematicheskie-ekskursii"],
] as const;

for(const [tz,slug,original] of refs){
 test(tz+" preserves official source link and marks source as not customer-approved",async({page})=>{
  await page.goto("/guide/"+slug+"/",{waitUntil:"domcontentloaded"});
  const main=page.locator("main");
  await expect(main.getByRole("heading",{level:1})).toBeVisible();
  await expect(main.getByRole("link",{name:/Открыть исходную страницу на действующем сайте музея/}))
    .toHaveAttribute("href","https://muzei-xleb.ru"+original);
  await expect(main).toContainText(/действующ(?:ем|его) сайт(?:е|а) музея/);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
 });
}
