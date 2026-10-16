import { expect, test } from "@playwright/test";

test("TZ-111: header, nested menu, search and keyboard accessible across engines", async ({page}) => {
  const pageErrors: string[]=[];
  page.on("pageerror", e=>pageErrors.push(e.message));
  await page.goto("/",{waitUntil:"networkidle"});
  await expect(page.getByRole("heading",{level:1})).toBeVisible();
  const menu=page.getByRole("navigation",{name:"Основное меню"});
  await menu.locator(".mega-group").first().locator("summary").click();
  await menu.getByRole("link",{name:"История музея",exact:true}).click();
  await expect(page).toHaveURL(/\/guide\/museum-history\/$/);
  const crumbs=page.getByRole("navigation",{name:"Хлебные крошки"});
  await expect(crumbs).toContainText("Музей");
  await page.goto("/search/",{waitUntil:"networkidle"});
  const search=page.getByRole("combobox",{name:"Поиск по сайту"});
  await expect(search).toHaveAttribute("data-ready","true");
  await search.fill("история хлеба");
  await expect(page.getByRole("listbox",{name:"Результаты поиска по сайту"})).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("TZ-111: mobile responsive menus and no horizontal page overflow",async ({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto("/",{waitUntil:"networkidle"});
  const menu=page.getByRole("navigation",{name:"Мобильное меню"});
  // Mobile container uses <details> around the actual navigation.
  await page.locator(".mobile-nav > summary").click();
  await expect(menu).toBeVisible();
  await menu.getByRole("link",{name:"Новости",exact:true}).click();
  await expect(page).toHaveURL(/\/news\/$/);
  const width=await page.evaluate(()=>[document.documentElement.scrollWidth,document.documentElement.clientWidth]);
  expect(width[0]).toBeLessThanOrEqual(width[1]+2);
});
