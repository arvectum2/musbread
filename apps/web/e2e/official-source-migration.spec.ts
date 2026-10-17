import {expect,test} from "@playwright/test";

test("existing source articles replace empty guide placeholders, preserving source link",async({page})=>{
  await page.goto("/guide/museum-history/");
  const copied=page.getByRole("region",{name:"Содержание действующего сайта музея"});
  await expect(copied).toBeVisible();
  await expect(copied).toContainText("1988");
  await expect(page.getByRole("link",{name:/исходную страницу/})).toHaveAttribute("href","https://muzei-xleb.ru/o-muzee");
});
test("legal documents show exact original museum PDF links and attribution",async({page})=>{
  await page.goto("/guide/museum-privacy/");
  await expect(page.getByRole("region",{name:"Содержание действующего сайта музея"})).toBeVisible();
  await expect(page.locator("main a[href$='20260203104919-1.pdf']").first()).toBeVisible();
  await expect(page.locator("main a[href$='20260203104920-1.pdf']").first()).toBeVisible();
});
test("museum header socials and footer official survey exist without PII forms",async({page})=>{
  await page.goto("/");
  const header=page.getByRole("navigation",{name:"Основное меню"});
  await expect(header.getByRole("link",{name:/ВКонтакте/})).toHaveAttribute("href","https://vk.com/club37126776");
  await expect(header.getByRole("link",{name:/MAX/})).toHaveAttribute("href","https://max.ru/id7808018523_gos");
  const footer=page.locator("footer");
  await expect(footer.getByRole("link",{name:/Оценить работу музея/})).toHaveAttribute("href",/sigmapro.givc.ru.*sid=256238/);
  await expect(page.locator("form[action*=survey]")).toHaveCount(0);
});
test("prices and source tables keep site usable on 320px viewport",async({page})=>{
  await page.setViewportSize({width:320,height:740});
  await page.goto("/guide/tickets-and-benefits/");
  const table=page.getByRole("region",{name:"Содержание действующего сайта музея"}).locator("table");
  await expect(table).toBeVisible();
  await expect(table).toContainText("400 рублей");
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(2);
  await page.goto("/");
  await page.locator(".mobile-nav summary").first().click();
  await expect(page.getByRole("navigation",{name:"Мобильное меню"}).getByRole("link",{name:/ВКонтакте/})).toBeVisible();
});


test("copied museum history is included in published static search", async({page}) => {
 await page.goto("/search/?q=Ленхлебпром");
 await expect(page.getByRole("link",{name:/История музея/}).first()).toHaveAttribute("href","/guide/museum-history/");
});


test("legacy cookie consent is cited, not presented as new site's own cookie policy",async({page})=>{
 await page.goto("/guide/museum-cookie/");
 await expect(page.locator("main")).toContainText("прежнем сайте музея");
 await expect(page.getByRole("region",{name:"Содержание действующего сайта музея"})).toHaveCount(0);
 await expect(page.getByRole("link",{name:/исходную страницу/})).toHaveAttribute("href","https://muzei-xleb.ru/my-ispolzuem-cookie");
});

test("museum exposition catalog retains real gallery names and official room links", async({page})=>{
 await page.goto("/guide/museum-exposition/");
 const catalog=page.getByRole("region",{name:"Залы постоянной экспозиции"});
 await expect(catalog).toBeVisible();
 await expect(catalog.locator(".exposition-card")).toHaveCount(11);
 await expect(catalog).toContainText("Зал «Хлеб в мировой истории»");
 await expect(catalog.locator('a[href^="https://muzei-xleb.ru/ekspozicii/"]')).toHaveCount(11);
});
