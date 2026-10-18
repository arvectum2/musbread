import {expect,test} from "@playwright/test";

test("TZ-136: three original museum video sections preserve 5+21+6 official headings",async({page})=>{
  await page.goto("/guide/museum-media/");
  const hub=page.getByRole("region",{name:"Официальные видео музея"});
  await expect(hub).toContainText("32 настоящих видеоматериала");
  const themes=hub.getByRole("group",{name:"Темы музейного видео"});
  await expect(themes.getByRole("button")).toHaveCount(3);
  await expect(themes.getByRole("button",{name:/О музее/})).toContainText("(5)");
  await expect(themes.getByRole("button",{name:/Выставки/})).toContainText("(21)");
  await expect(themes.getByRole("button",{name:/НЕобзорная экскурсия/})).toContainText("(6)");
  await expect(hub.locator(".official-video-card")).toHaveCount(5);
  await expect(hub.locator("iframe")).toHaveCount(0);
  await themes.getByRole("button",{name:/Выставки/}).click();
  await expect(hub.locator(".official-video-card")).toHaveCount(21);
  await expect(hub.locator("iframe")).toHaveCount(0);
  await expect(hub).toContainText("Открытие выставки");
  await expect(hub.getByRole("link",{name:/Открыть оригинальное видео телеканала/}))
    .toHaveAttribute("href",/^https:\/\/cdnvideo\.tvspb\.ru\/.*\.mp4$/);
  await themes.getByRole("button",{name:/НЕобзорная экскурсия/}).click();
  await expect(hub.locator(".official-video-card")).toHaveCount(6);
  await expect(hub).toContainText("Медогонка");
});

test("TZ-202: no passive VK requests, explicit click creates one strictly sandboxed video embed",async({page})=>{
  const external:string[]=[];
  await page.route(/https:\/\/(vk\.com|vkvideo\.ru)\//,route=>{
    external.push(route.request().url());
    return route.abort();
  });
  await page.goto("/guide/museum-media/");
  const hub=page.getByRole("region",{name:"Официальные видео музея"});
  expect(external).toEqual([]);
  await expect(hub.locator("iframe")).toHaveCount(0);
  const cards=hub.locator(".official-video-card");
  await expect(cards).toHaveCount(5);
  await cards.first().getByRole("button",{name:"Посмотреть видео"}).click();
  await expect(hub.locator("iframe")).toHaveCount(1);
  const player=cards.first().locator("iframe");
  await expect(player).toHaveAttribute("src",/^https:\/\/vk\.com\/video_ext\.php\?/);
  await expect(player).toHaveAttribute("src",/oid=-37126776/);
  await expect(player).toHaveAttribute("referrerpolicy","no-referrer");
  await expect(player).toHaveAttribute("sandbox",/allow-scripts/);
  await expect(player).toHaveAttribute("title",/Репортаж о музее/);
  await expect.poll(()=>external.length).toBeGreaterThan(0);
  await expect(cards.first().locator("iframe")).toHaveCount(1);
  await cards.first().getByRole("button",{name:"Закрыть видео"}).click();
  await expect(hub.locator("iframe")).toHaveCount(0);
});

test("TZ-202: opening another original player stops the previous third-party frame",async({page})=>{
  await page.route(/https:\/\/(vk\.com|vkvideo\.ru)\//,route=>route.abort());
  await page.goto("/guide/museum-media/");
  const hub=page.getByRole("region",{name:"Официальные видео музея"});
  const cards=hub.locator(".official-video-card");
  await cards.first().getByRole("button",{name:"Посмотреть видео"}).click();
  await expect(cards.first().locator("iframe")).toHaveCount(1);
  await cards.nth(1).getByRole("button",{name:"Посмотреть видео"}).click();
  await expect(cards.first().locator("iframe")).toHaveCount(0);
  await expect(cards.nth(1).locator("iframe")).toHaveCount(1);
  await hub.getByRole("button",{name:/Выставки/}).click();
  await expect(hub.locator("iframe")).toHaveCount(0);
  await expect(hub.locator(".official-video-card")).toHaveCount(21);
});

test("museum video archive can be operated with keyboard and remains within 320px",async({page})=>{
  await page.setViewportSize({width:320,height:740});
  await page.goto("/guide/museum-media/");
  const hub=page.getByRole("region",{name:"Официальные видео музея"});
  await hub.getByRole("button",{name:/Выставки/}).focus();
  await page.keyboard.press("Enter");
  await expect(hub.locator(".official-video-card")).toHaveCount(21);
  const firstVk=hub.locator(".official-video-card").nth(1);
  await firstVk.getByRole("button",{name:"Посмотреть видео"}).focus();
  await page.keyboard.press("Space");
  await expect(firstVk.locator("iframe")).toHaveCount(1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
  await firstVk.getByRole("button",{name:"Закрыть видео"}).focus();
  await page.keyboard.press("Enter");
  await expect(firstVk.locator("iframe")).toHaveCount(0);
});
