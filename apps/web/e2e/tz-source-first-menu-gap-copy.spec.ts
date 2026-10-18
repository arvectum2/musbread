import {test,expect} from "@playwright/test";

test("Original museum legal menu materials and their actual PDF anchors copied",async({page})=>{
  for(const [slug,heading,source,minimumPdf] of [
    ["museum-accounting-policy","Учётная политика","/uchetnaya-politika",7],
    ["museum-anti-terror","Противодействие терроризму","/protivodeystvie-terrorizmu",3],
    ["museum-antimonopoly","Антимонопольный комплаенс","/antimonopolnyy-komplaens",1],
  ] as const){
    await page.goto("/guide/"+slug+"/");
    await expect(page.locator("h1")).toContainText(heading.slice(0,7));
    const original=page.getByRole("region",{name:"Содержание действующего сайта музея"});
    await expect(original).toBeVisible();
    const pdf=original.locator('a[href^="https://muzei-xleb.ru/sites/default/files/page/"][href$=".pdf"]');
    await expect(pdf).toHaveCount(minimumPdf);
    await expect(page.getByRole("link",{name:/Открыть исходную страницу на действующем сайте музея/}))
      .toHaveAttribute("href","https://muzei-xleb.ru"+source);
  }
});

test("Museum address directions now copied from official page, not invented",async({page})=>{
  await page.goto("/guide/plan-visit/");
  const actual=page.getByRole("region",{name:"Как добраться: официальная инструкция музея"});
  await expect(actual).toBeVisible();
  await expect(actual).toContainText("Финляндский вокзал");
  await expect(actual).toContainText("улице Комсомола");
  await expect(actual.getByRole("link",{name:/оригинальная инструкция/}))
    .toHaveAttribute("href","https://muzei-xleb.ru/adres");
});

test("Old guestbook visitor message and 2021 covid restrictions never shown as new museum policy",async({page})=>{
  await page.goto("/guide/museum-feedback/");
  await expect(page.locator("main")).not.toContainText("Ребята счастливы!");
  await page.goto("/guide/plan-visit/");
  await expect(page.locator("main")).not.toContainText("защитных масок и перчаток");
});
