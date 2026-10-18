import {expect,test} from "@playwright/test";

test("TZ-161 children workshops show twelve original programs and source ages",async({page})=>{
  await page.goto("/guide/children-workshops/");
  const listing=page.getByRole("region",{name:"Мастер-классы по действующему каталогу музея"});
  const cards=listing.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(12);
  await expect(cards.first()).toContainText("Кувадка");
  await cards.first().locator("summary").click();
  await expect(cards.first()).toContainText("Возраст: 6+");
  await expect(listing).toContainText("Роспись изразца");
  await expect(listing.locator('a[href^="https://muzei-xleb.ru/master-klassy/"]')).toHaveCount(11);
  await expect(listing.locator('a[href^="https://muzei-xleb.ru/ekskursii/master-klass-"]')).toHaveCount(1);
  await expect(listing.locator("img")).toHaveCount(0);
});

test("TZ-158 adult workshop page distinguishes actual catalogue from adult eligibility",async({page})=>{
  await page.goto("/guide/excursion-workshops-adults/");
  const listing=page.getByRole("region",{name:"Мастер-классы по действующему каталогу музея"});
  await expect(listing.locator(".official-museum-program-card")).toHaveCount(12);
  await expect(listing).toContainText("Отдельного утверждённого музеем каталога");
  await expect(listing).toContainText("возможность участия взрослых нужно уточнить");
  await expect(page.locator("main")).not.toContainText("Этот раздел требуется ТЗ, но сведения");
});

test("TZ-145 shop renders an honest CMS-ready empty catalogue and no web sales",async({page})=>{
  await page.goto("/guide/museum-shop/");
  const shop=page.getByRole("region",{name:"Витрина музейного магазина без продажи"});
  await expect(shop).toContainText("Каталог сувениров уточняется");
  await expect(shop).toContainText("нет корзины, оформления заказа или онлайн-оплаты");
  await expect(shop.locator(".museum-shop-item")).toHaveCount(0);
  await expect(shop.locator("form")).toHaveCount(0);
  await expect(shop.locator("button")).toHaveCount(0);
  await expect(shop.locator('a[href^="mailto:"]')).toHaveCount(0);
  await expect(shop.locator('a[href^="tel:"]')).toHaveCount(1);
  await expect(shop).not.toContainText("Добавить в корзину");
});

test("TZ-145/161 pages fit a 320px phone and native disclosure is keyboard operable",async({page})=>{
  await page.setViewportSize({width:320,height:695});
  for(const path of ["/guide/museum-shop/","/guide/children-workshops/","/guide/excursion-workshops-adults/"]){
    await page.goto(path);
    const extent=await page.evaluate(()=>({
      doc:document.documentElement.scrollWidth,
      viewport:document.documentElement.clientWidth,
    }));
    expect(extent.doc).toBeLessThanOrEqual(extent.viewport+1);
  }
  const first=page.locator(".official-museum-program-card").first().locator("summary");
  await first.focus();
  await page.keyboard.press("Enter");
  await expect(first.locator("..")).toHaveAttribute("open","");
});
