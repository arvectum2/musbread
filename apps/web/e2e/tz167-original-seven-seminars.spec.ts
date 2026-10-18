import {expect,test} from "@playwright/test";

test("TZ-167 seven real past scientific seminars and sixteen original recordings",async({page})=>{
  await page.goto("/guide/science-conferences/");
  const portal=page.getByRole("region",{name:"Семинары и научные конференции"});
  const archive=portal.getByRole("region",{name:"Реальные научные семинары музея"});
  await expect(archive).toContainText("7 научных мероприятий 2020–2026 годов");
  await expect(archive).toContainText("16 видеозаписей");
  await expect(archive.locator(".official-museum-program-card")).toHaveCount(7);
  await expect(archive).toContainText("К истории мукомольных мельниц");
  await expect(archive).toContainText("Купцы-хлеботорговцы в Петербурге");
  await expect(archive).toContainText("Проблемы доставки продовольствия в блокированный Ленинград");
  await expect(archive).toContainText("16.04.2026");
  await expect(archive).toContainText("10.11.2020");
  await expect(archive.getByRole("link",{name:/Оригинальная страница научного семинара/}))
    .toHaveCount(7);
  await expect(archive.getByRole("button",{name:/Просмотреть запись/})).toHaveCount(16);
  await expect(archive.locator("iframe")).toHaveCount(0);
  await expect(portal).toContainText("Подтверждённых предстоящих научных");
});

test("TZ-167 seminar videos never load VK before click; only one frame active",async({page})=>{
  const external:string[]=[];
  await page.route(/https:\/\/(vk\.com|vkvideo\.ru)\//,route=>{
    external.push(route.request().url());
    return route.abort();
  });
  await page.goto("/guide/science-conferences/");
  const archive=page.getByRole("region",{name:"Реальные научные семинары музея"});
  expect(external).toEqual([]);
  const first=archive.locator(".official-museum-program-card").first();
  const open=first.getByRole("button",{name:/Просмотреть запись/});
  await open.first().click();
  await expect(archive.locator("iframe")).toHaveCount(1);
  await expect(first.locator("iframe")).toHaveAttribute("src",/^https:\/\/vk\.com\/video_ext\.php\?/);
  await expect(first.locator("iframe")).toHaveAttribute("sandbox",/allow-scripts/);
  await expect(first.locator("iframe")).toHaveAttribute("referrerpolicy","no-referrer");
  await expect.poll(()=>external.length).toBeGreaterThan(0);
  await first.getByRole("button",{name:/Закрыть запись/}).first().click();
  await expect(archive.locator("iframe")).toHaveCount(0);
});

test("Original scientific seminar video controls are keyboard accessible at 320px",async({page})=>{
  await page.setViewportSize({width:320,height:720});
  await page.goto("/guide/science-conferences/");
  const archive=page.getByRole("region",{name:"Реальные научные семинары музея"});
  const button=archive.getByRole("button",{name:/Просмотреть запись/}).first();
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(archive.locator("iframe")).toHaveCount(1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth))
    .toBeLessThanOrEqual(2);
});
