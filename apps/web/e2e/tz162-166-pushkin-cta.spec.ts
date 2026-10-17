import {expect,test} from "@playwright/test";

for (const route of ["/guide/children/","/guide/children-pushkin-card/","/guide/exhibitions-guide/","/guide/exhibitions-pushkin-card/"]){
 test("TZ-162/166 official Pushkin-card CTA is visible and safe on "+route,async({page})=>{
  await page.goto(route,{waitUntil:"domcontentloaded"});
  const section=page.getByRole("region",{name:"Переход к Пушкинской карте"});
  await expect(section.getByRole("heading",{name:"«Пушкинская карта»"})).toBeVisible();
  const action=section.getByRole("link",{name:/Открыть «Пушкинскую карту» на сайте музея/});
  await expect(action).toBeVisible();
  await expect(action).toHaveAttribute("href","https://muzei-xleb.ru/pushkinskaya-karta");
  await expect(action).toHaveAttribute("rel",/noopener/);
  await expect(action).toHaveAttribute("target","_blank");
  await expect(section).toContainText("Участие конкретного мероприятия");
  const pii=page.locator('form[action*="pushkin"],input[name="email"],iframe');
  await expect(pii).toHaveCount(0);
 });
}
