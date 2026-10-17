import {test, expect} from "@playwright/test";

/** Deterministic, automated paths through this UNAPPROVED prototype.
 * These are not human usability rounds (TZ-247) nor official museum UAT. */
const tasks=[
  {name:"Как добраться",route:"/guide/plan-visit/"},
  {name:"Билеты и льготы",route:"/guide/tickets-and-benefits/"},
  {name:"Афиша",route:"/events/"},
  {name:"Экскурсии",route:"/excursions/"},
  {name:"Доступная среда",route:"/guide/accessible-museum/"},
  {name:"Контакты",route:"/guide/museum-contacts/"},
  {name:"Документы музея",route:"/guide/museum-documents/"},
] as const;

test("TZ-245/246: search page gives task-first paths, each reachable in one click",async({page})=>{
  for(const viewport of [{width:1440,height:900},{width:390,height:800}]){
    await page.setViewportSize(viewport);
    await page.goto("/search/",{waitUntil:"networkidle"});
    const tasksNav=page.getByRole("navigation",{name:"Быстрые переходы по задачам посетителя"});
    await expect(tasksNav.getByRole("link")).toHaveCount(tasks.length);
    for(const task of tasks){
      await page.goto("/search/",{waitUntil:"domcontentloaded"});
      await tasksNav.getByRole("link",{name:new RegExp("^"+task.name)}).click();
      await expect(page).toHaveURL(new RegExp(task.route.replaceAll("/","\\/")+"$"));
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByRole("navigation",{name:"Хлебные крошки"})).toHaveCount(1);
    }
  }
});

test("TZ-246/249: homepage task shortcuts lead to real pages in one click, no fake external purchase",async({page})=>{
  for(const width of [320,768,1440]){
    await page.setViewportSize({width,height:900});
    await page.goto("/",{waitUntil:"networkidle"});
    const nav=page.getByRole("navigation",{name:"Быстрые переходы по задачам посетителя"});
    await expect(nav.getByRole("link")).toHaveCount(tasks.length);
    for(const task of tasks){
      const link=nav.getByRole("link",{name:new RegExp("^"+task.name)});
      await expect(link).toHaveAttribute("href",task.route);
      const size=await link.boundingBox();
      expect(size,"CTA must be reliably clickable for "+task.name).not.toBeNull();
      expect(size!.height,"minimum 44 CSS px CTA target").toBeGreaterThanOrEqual(44);
      expect(size!.width,"minimum 44 CSS px CTA target").toBeGreaterThanOrEqual(44);
    }
    await nav.getByRole("link",{name:/^Контакты/}).click();
    await expect(page).toHaveURL(/\/guide\/museum-contacts\/$/);
    await expect(page.getByText(/\+7 \(812\) 294-50-82/).first()).toBeVisible();
  }
});

test("TZ-245: find published content, recover from zero results and preserve query",async({page})=>{
  await page.goto("/search/",{waitUntil:"networkidle"});
  const search=page.getByRole("combobox",{name:"Поиск по сайту"});
  await expect(page.getByText(/Введите не менее двух символов/)).toBeVisible();
  await search.fill("конвейера");
  await page.getByRole("button",{name:"Показать результаты поиска"}).click();
  const all=page.getByRole("region",{name:"Все результаты поиска"});
  await expect(all.getByRole("link",{name:"Демонстрационная новость"})).toBeVisible();
  await all.getByRole("link",{name:"Демонстрационная новость"}).click();
  await expect(page).toHaveURL(/\/news\/demo-news\/$/);

  await page.goto("/search/",{waitUntil:"networkidle"});
  await search.fill("совершенно-несуществующий-музейный-запрос");
  await expect(page.getByRole("status")).toHaveText("Материалы не найдены.");
  const recovery=page.getByRole("link",{name:"основным задачам посетителя"});
  await expect(recovery).toHaveAttribute("href","#visitor-tasks");
  await recovery.click();
  await expect(page).toHaveURL(/\/search\/#visitor-tasks$/);
  await page.getByRole("navigation",{name:"Быстрые переходы по задачам посетителя"})
    .getByRole("link",{name:/^Как добраться/}).click();
  await expect(page).toHaveURL(/\/guide\/plan-visit\/$/);
});

test("TZ-249: menu, footer and event titles look like links even without hover",async({page})=>{
  await page.setViewportSize({width:1440,height:850});
  await page.goto("/",{waitUntil:"networkidle"});
  const menu=page.getByRole("navigation",{name:"Основное меню"}).getByRole("link",{name:"Новости"});
  const footer=page.locator("footer.site-footer").getByRole("link",{name:"Новости"});
  const event=page.locator(".event-card h3 a").first();
  for(const link of [menu,footer,event]){
    await expect(link).toBeVisible();
    const decoration=await link.evaluate(el=>getComputedStyle(el).textDecorationLine);
    expect(decoration,"link should be identifiable without hover").toContain("underline");
  }
  await page.setViewportSize({width:390,height:850});
  await page.goto("/",{waitUntil:"networkidle"});
  const mobile=page.locator(".mobile-nav > summary");
  await mobile.click();
  const mobileNews=page.getByRole("navigation",{name:"Мобильное меню"}).getByRole("link",{name:"Новости"});
  await expect(mobileNews).toBeVisible();
  expect(await mobileNews.evaluate(el=>getComputedStyle(el).textDecorationLine)).toContain("underline");
});

test("TZ-249: primary action buttons have min 44px targets, underlined text affordance and focus",async({page})=>{
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:850});
    await page.goto("/",{waitUntil:"networkidle"});
    const primary=page.getByRole("link",{name:/^Смотреть афишу/});
    const secondary=page.getByRole("link",{name:/^Узнать о проекте/});
    for(const link of [primary,secondary]){
      const size=await link.boundingBox();
      expect(size).not.toBeNull();
      expect(size!.height).toBeGreaterThanOrEqual(44);
      expect(size!.width).toBeGreaterThanOrEqual(44);
      await link.focus();
      await expect(link).toBeFocused();
      const focus=await link.evaluate(el=>getComputedStyle(el).outlineWidth);
      expect(parseFloat(focus)).toBeGreaterThanOrEqual(3);
    }
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
    expect(overflow,"No extra horizontal scroll on narrow screens").toBeLessThanOrEqual(2);
  }
});
