import {expect,test} from "@playwright/test";

test("TZ-167 science conferences show seven source-verified historical seminars, while future CMS calendar remains empty",async({page})=>{
  await page.goto("/guide/science-conferences/");
  const area=page.getByRole("region",{name:"Семинары и научные конференции"});
  await expect(area).toContainText("Подтверждённых предстоящих научных");
  await expect(area.getByRole("region",{name:"Реальные научные семинары музея"})
    .locator(".official-museum-program-card")).toHaveCount(7);
  await expect(area.locator(".event-card")).toHaveCount(0);
  await expect(area).not.toContainText("Демонстрационная экскурсия");
});

test("TZ-168 publications require real bibliography, not misleading scientific department PDFs",async({page})=>{
  await page.goto("/guide/science-publications/");
  const area=page.getByRole("region",{name:"Научные публикации музея"});
  await expect(area).toContainText("Подтверждённая библиография");
  await expect(area).toContainText("Положения об организации музея не являются");
  await expect(area.locator(".museum-list-item")).toHaveCount(0);
});

test("TZ-169/170 collection source links to exactly museum's original Goskatalog ID",async({page})=>{
  await page.goto("/guide/science-collection/");
  const area=page.getByRole("region",{name:"Музейная коллекция"});
  await expect(area.getByRole("link",{name:/Госкаталоге/})).toHaveAttribute("href",
    "https://goskatalog.ru/portal/#/collections?museumIds=1200");
  await expect(page.getByRole("link",{name:/Госкаталоге/})).toHaveCount(1);
  await expect(area).toContainText("не предоставлен");
  await expect(area.locator("img")).toHaveCount(0);
});

test("TZ-171 researcher guidance links real original museum policy without invented access privilege",async({page})=>{
  await page.goto("/guide/science-researchers/");
  const area=page.getByRole("region",{name:"Информация для исследователей"});
  await expect(area.getByRole("link",{name:/Положение о порядке и условиях доступа/})).toHaveAttribute(
    "href","https://muzei-xleb.ru/sites/default/files/page/20260203112347-poryadok_dostupa.pdf");
  await expect(area).toContainText("не гарантирует доступ в фонды");
  await expect(area.locator("form")).toHaveCount(0);
});

test("TZ-172 two actual source-based scientific organizational documents visible",async({page})=>{
  await page.goto("/guide/science-materials/");
  const area=page.getByRole("region",{name:"Научные и научно-организационные материалы"});
  await expect(area.locator(".official-museum-program-card")).toHaveCount(2);
  await expect(area).toContainText("2025 — 2035 гг.");
  await expect(area).toContainText("Научно-методическом совете");
  await expect(area.locator('a[href$=".pdf"]')).toHaveCount(1);
  await expect(area.locator('a[href$=".docx"]')).toHaveCount(1);
  await expect(area.locator("img")).toHaveCount(0);
});

test("scientific pages fit 320px and still preserve official document links",async({page})=>{
  await page.setViewportSize({width:320,height:680});
  for(const route of [
    "/guide/science-conferences/","/guide/science-publications/",
    "/guide/science-collection/","/guide/science-researchers/","/guide/science-materials/",
  ]){
    await page.goto(route);
    const w=await page.evaluate(()=>({document:document.documentElement.scrollWidth,
      viewport:document.documentElement.clientWidth}));
    expect(w.document).toBeLessThanOrEqual(w.viewport+1);
  }
});
