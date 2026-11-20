import {expect,test} from "@playwright/test";

const routes=[
 {route:"agenda-children",name:"Детям",visible:0},
 {route:"agenda-meetings",name:"Встречи",visible:0},
 {route:"agenda-festivals",name:"Фестивали",visible:0},
 {route:"agenda-workshops",name:"Мастер-классы",visible:1},
 {route:"agenda-archive",name:"Архив",visible:0},
];
for(const {route,name,visible} of routes){
 test("TZ-149/151/152/153: "+name+" uses published CMS events only",async({page})=>{
  // Fixed time belongs only to the synthetic fixture scenario; never to the production clock.
  await page.clock.setFixedTime(new Date("2026-11-01T12:00:00Z"));
  await page.goto("/guide/"+route+"/");
  const category=page.getByRole("region",{name:"Мероприятия раздела: "+name});
  await expect(category).toBeVisible();
  await expect(category.locator(".event-agenda")).toHaveAttribute("data-ready","true");
  await expect(category).toContainText("Демонстрационные записи не являются официальным расписанием");
  await expect(category.getByRole("link",{name:/официальном действующем сайте/})).toHaveAttribute("href","https://muzei-xleb.ru/novosty");
  await expect(category.locator(".event-card")).toHaveCount(visible);
  if(visible===0){
   await expect(category.getByRole("status")).toContainText(
    route==="agenda-archive" ? "В архиве пока нет" : "Предстоящих мероприятий пока нет"
   );
  } else {
   await expect(category.locator(".event-card")).toContainText("Мастер-класс");
   await expect(category.locator(".event-card a[href='/events/workshop/']").first()).toBeVisible();
  }
  await expect(category.getByRole("combobox",{name:"Категория мероприятий"})).toBeVisible();
  await page.setViewportSize({width:320,height:760});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
 });
}

// Retain a separate boundary case after all three dated public fixtures have ended.
if (process.env.MUSBREAD_CI_PUBLIC_FIXTURES) {
 test("TZ-149/153: expired public fixtures migrate to archive without changing detail links",async({page})=>{
  await page.clock.setFixedTime(new Date("2026-11-20T12:00:00Z"));
  await page.goto("/guide/agenda-workshops/");
  const upcoming=page.getByRole("region",{name:"Мероприятия раздела: Мастер-классы"});
  await expect(upcoming.locator(".event-agenda")).toHaveAttribute("data-ready","true");
  await expect(upcoming.locator(".event-card")).toHaveCount(0);
  await page.goto("/guide/agenda-archive/");
  const archived=page.getByRole("region",{name:"Мероприятия раздела: Архив"});
  await expect(archived.locator(".event-agenda")).toHaveAttribute("data-ready","true");
  await expect(archived.locator(".event-card")).toHaveCount(3);
  for (const slug of ["bread-history","workshop","exhibition"]) {
   await expect(archived.locator(`a[href="/events/${slug}/"]`).first()).toBeVisible();
  }
 });
}
