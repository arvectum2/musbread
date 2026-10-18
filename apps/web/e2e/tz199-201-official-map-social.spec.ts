import {expect,test} from "@playwright/test";

const museumMap="https://yandex.ru/map-widget/v1/?um=constructor%3AHe-zSYLQhEw4RVkaykZ0Rpr1lOWx3f9O&source=constructor";

test("TZ-199: pinned original Yandex constructor does not contact third parties before opt-in",async({page})=>{
  const mapRequests:string[]=[];
  await page.route("**/yandex.ru/**",route=>{
    mapRequests.push(route.request().url());
    return route.abort();
  });
  await page.goto("/guide/museum-contacts/");
  const widget=page.getByRole("region",{name:"Как добраться: карта музея"});
  await expect(widget.getByRole("button",{name:"Показать карту музея"})).toBeVisible();
  await expect(widget.locator("iframe")).toHaveCount(0);
  await expect(widget).toContainText("только по вашему нажатию");
  expect(mapRequests).toEqual([]);
  await widget.getByRole("button",{name:"Показать карту музея"}).click();
  await expect(widget.locator("iframe")).toHaveCount(1);
  await expect(widget.locator("iframe")).toHaveAttribute("src",museumMap);
  await expect(widget.locator("iframe")).toHaveAttribute("referrerpolicy","no-referrer");
  await expect(widget.locator("iframe")).toHaveAttribute("sandbox",/allow-scripts/);
  await expect.poll(()=>mapRequests.length).toBeGreaterThan(0);
  await widget.getByRole("button",{name:"Скрыть карту"}).click();
  await expect(widget.locator("iframe")).toHaveCount(0);
  await expect(widget.getByRole("button",{name:"Показать карту музея"})).toHaveAttribute("aria-expanded","false");
});

test("TZ-199: museum map is on planning route, and accessible using keyboard only",async({page})=>{
  await page.goto("/guide/plan-visit/");
  const widget=page.getByRole("region",{name:"Как добраться: карта музея"});
  await expect(widget.getByRole("link",{name:/Открыть адрес в Яндекс Картах/}))
    .toHaveAttribute("href",/^https:\/\/yandex\.ru\/maps\/\?text=/);
  const button=widget.getByRole("button",{name:"Показать карту музея"});
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(widget.locator("iframe")).toHaveAttribute("title",/Санкт-Петербургского музея Хлеба/);
  await widget.getByRole("button",{name:"Скрыть карту"}).focus();
  await page.keyboard.press("Space");
  await expect(widget.locator("iframe")).toHaveCount(0);
});

test("TZ-201: VK/MAX are source verified, directly linked and never embedded as third-party widgets",async({page})=>{
  await page.goto("/guide/museum-contacts/");
  const area=page.getByRole("region",{name:"Официальные сообщества музея"});
  await expect(area).toContainText("официальных контактах музея");
  await expect(area.getByRole("link",{name:/ВКонтакте — сообщество/}))
    .toHaveAttribute("href","https://vk.com/club37126776");
  await expect(area.getByRole("link",{name:/MAX — канал/}))
    .toHaveAttribute("href","https://max.ru/id7808018523_gos");
  for(const href of ["https://vk.com/club37126776","https://max.ru/id7808018523_gos"]){
    // Header deliberately has desktop and mobile navigations.
    await expect(page.locator("header a[href='"+href+"']")).toHaveCount(2);
    await expect(page.locator("footer a[href='"+href+"']")).toHaveCount(1);
    await expect(area.locator('a[href="'+href+'"]')).toHaveAttribute("rel",/noopener/);
  }
  await expect(area.locator("iframe")).toHaveCount(0);
});

test("contact map and museum network links do not overflow 320px",async({page})=>{
  await page.setViewportSize({width:320,height:690});
  for(const path of ["/guide/museum-contacts/","/guide/plan-visit/"]){
    await page.goto(path);
    const map=page.getByRole("region",{name:"Как добраться: карта музея"});
    await expect(map).toBeVisible();
    await expect(page.getByRole("region",{name:"Официальные сообщества музея"})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-
      document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
  }
});
