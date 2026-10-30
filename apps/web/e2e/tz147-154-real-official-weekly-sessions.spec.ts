import {expect,test} from "@playwright/test";

// Reproduce the original museum bulletin's October 18 snapshot; these
// historical 5/119 counts are not unconditional live future availability.
const bulletinSnapshotTime = new Date("2026-10-18T09:00:00+03:00");


test("six museum weekly programmes yield 124 real dated sessions, 5 on Oct 18-19",async({page})=>{
  await page.clock.setFixedTime(bulletinSnapshotTime);
  await page.goto("/events/");
  const area=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(area).toContainText("140 строк");
  await expect(area).toContainText("124 отдельных сеанса");
  await expect(area.getByRole("button",{name:/По расписанию/})).toContainText("(5)");
  await expect(area.getByRole("button",{name:/Архив/})).toContainText("(119)");
  const cards=area.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(5);
  await expect(cards.first()).toContainText("Героя хлеб кормит");
  await expect(area).toContainText("14:00");
  await expect(area).toContainText("19.10.2026");
  await expect(area.locator('a[href^="https://muzei-xleb.ru/novosty/"]')).toHaveCount(5);
  await expect(area).toContainText("продолжительность и доступность записи не подтверждены");
});

test("museum Sep-Oct archived sessions remain dated and fully expandable",async({page})=>{
  await page.clock.setFixedTime(bulletinSnapshotTime);
  await page.goto("/guide/agenda-archive/");
  const area=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(area.getByRole("button",{name:/Показать все 119 подтверждённых записей/})).toBeVisible();
  await expect(area.locator(".official-museum-program-card")).toHaveCount(15);
  await area.getByRole("button",{name:/Показать все 119 подтверждённых записей/}).click();
  await expect(area.locator(".official-museum-program-card")).toHaveCount(119);
  await expect(area).toContainText("07.09.2026");
  await expect(area).toContainText("17.10.2026");
  await expect(area.locator("img")).toHaveCount(0);
});

test("excursion category holds 100 original sessions with real source dates, not generic guesses",async({page})=>{
  await page.clock.setFixedTime(bulletinSnapshotTime);
  await page.goto("/guide/agenda-excursions/");
  const area=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(area).toContainText("18.10.2026");
  await expect(area.locator(".official-museum-program-card")).toHaveCount(5);
  await area.getByRole("button",{name:/Архив/}).click();
  await expect(area.getByRole("button",{name:/Показать все 95 подтверждённых записей/})).toBeVisible();
});

test("all fifteen dated workshop sessions in archive, no invented future master classes",async({page})=>{
  await page.goto("/guide/agenda-workshops/");
  const area=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(area).toContainText("нет подтверждённых будущих сеансов");
  await area.getByRole("button",{name:/Архив/}).click();
  await expect(area.locator(".official-museum-program-card")).toHaveCount(15);
  await expect(area).toContainText("Мастер-класс");
  await expect(area).toContainText("Кувадк");
});

test("age-filter is exact and not claimed as children-only; festivals missing no fake data",async({page})=>{
  await page.goto("/guide/agenda-children/");
  const child=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(child).toContainText("от 5+ до 10+");
  await expect(child).toContainText("не утверждение, что программы");
  await child.getByRole("button",{name:/Архив/}).click();
  await expect(child).toContainText("Показать все");
  await page.goto("/guide/agenda-festivals/");
  const fest=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(fest).toContainText("нет подтверждённых отдельных фестивальных сеансов");
  await expect(fest.locator(".official-museum-program-card")).toHaveCount(0);
});

test("source schedules are accessible on 320px without fake images or horizontal overflow",async({page})=>{
  await page.setViewportSize({width:320,height:720});
  for(const path of ["/events/","/guide/agenda-excursions/","/guide/agenda-workshops/","/guide/agenda-archive/"]){
    await page.goto(path);
    await expect(page.locator(".official-agenda-sessions")).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
  }
});


test("expired historical bulletin sessions are not presented as upcoming in October 2026", async ({page})=>{
  await page.clock.setFixedTime(new Date("2026-10-30T09:00:00+03:00"));
  await page.goto("/events/");
  const area=page.getByRole("region",{name:"Проверенные сеансы из официальных недельных афиш музея"});
  await expect(area.getByRole("button",{name:/По расписанию/})).toContainText("(0)");
  await expect(area.getByRole("button",{name:/Архив/})).toContainText("(124)");
  await expect(area).toContainText("нет подтверждённых будущих сеансов");
});
