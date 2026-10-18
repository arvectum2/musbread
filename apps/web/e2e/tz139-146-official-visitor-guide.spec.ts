import {expect,test} from "@playwright/test";

test("TZ-146: factual FAQ presents nine official-source-linked questions, keyboard operable",async({page})=>{
  await page.goto("/guide/faq/");
  const faq=page.getByRole("region",{name:"Частые вопросы о посещении музея"});
  const questions=faq.locator("details");
  await expect(questions).toHaveCount(9);
  await questions.first().locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(questions.first()).toHaveAttribute("open","");
  await expect(questions.first()).toContainText("10:00 до 18:00");
  const urls=await faq.locator(".visitor-faq-answer a").evaluateAll(
    els=>els.map(x=>(x as HTMLAnchorElement).href),
  );
  expect(urls).toHaveLength(9);
  expect(urls.every(u=>u.startsWith("https://muzei-xleb.ru/"))).toBe(true);
  await expect(faq).toContainText("Вопросы подготовлены для нового сайта");
  await expect(page.locator("main")).not.toContainText("сведения на действующем сайте не найдены");

  await expect(faq).not.toContainText("обязательные маски");
});

test("TZ-139: visitor planning distinguishes excursion policy from general visitor rules",async({page})=>{
  await page.goto("/guide/plan-visit/");
  const guide=page.getByRole("region",{name:"Перед посещением: условия экскурсий"});
  await expect(guide).toContainText("только по предварительной записи");
  await expect(guide).toContainText("до 20 детей");
  await expect(guide).toContainText("50–60 минут");
  await expect(guide).toContainText("только без вспышки");
  await expect(guide).toContainText("не заменяют официальный полный регламент");
  await expect(guide.locator('a[href^="https://muzei-xleb.ru/sites/default/files/page/"]')).toHaveCount(1);
  await expect(guide.getByRole("link",{name:/частые вопросы/})).toHaveAttribute("href","/guide/faq/");
});

test("TZ-139/146: visitor FAQ stays usable at 320px with no horizontal scroll",async({page})=>{
  await page.setViewportSize({width:320,height:720});
  for(const path of ["/guide/faq/","/guide/plan-visit/"]){
    await page.goto(path);
    await expect(page.getByRole("heading",{level:1})).toBeVisible();
    const result=await page.evaluate(()=>({
      actual:document.documentElement.scrollWidth,
      viewport:document.documentElement.clientWidth,
    }));
    expect(result.actual).toBeLessThanOrEqual(result.viewport+1);
  }
});
