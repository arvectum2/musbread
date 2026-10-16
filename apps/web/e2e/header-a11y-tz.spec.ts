import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("TZ-115: all 7 top-level sections and approved deep navigation available at desktop and mobile widths", async ({page}) => {
  await page.goto("/",{waitUntil:"networkidle"});
  const groups=page.getByRole("navigation",{name:"Основное меню"});
  await expect(groups.locator(".mega-group")).toHaveCount(7);
  for(const name of ["Музей","Посетителям","Афиша","Экскурсии","Детям","Выставки","Наука"]){
    await expect(groups.locator("summary").filter({hasText:name})).toHaveCount(1);
  }
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator(".mobile-nav > summary")).toBeVisible();
  await page.locator(".mobile-nav > summary").click();
  const mobile=page.getByRole("navigation",{name:"Мобильное меню"});
  for(const name of ["Музей","Посетителям","Афиша","Экскурсии","Детям","Выставки","Наука"]){
    await expect(mobile.locator("summary").filter({hasText:name})).toHaveCount(1);
  }
});

test("TZ-117/TZ-118: vision and access controls visible at desktop, tablet, mobile, persisted",async ({page})=>{
 await page.goto("/",{waitUntil:"networkidle"});
 for(const width of [1440,1024,960,768,390,320]){
   await page.setViewportSize({width,height:850});
   const accessibility=page.getByRole("link",{name:"Доступная среда: условия посещения"});
   const vision=page.getByRole("button",{name:"Для слабовидящих"});
   await expect(accessibility).toBeVisible();
   await expect(vision).toBeVisible();
   const box=await accessibility.boundingBox();
   expect(box).not.toBeNull();
   expect(box!.x).toBeGreaterThanOrEqual(-1);
   expect(box!.x+box!.width).toBeLessThanOrEqual(width+1);
   const horizontalOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
   expect(horizontalOverflow, `overflow at viewport ${width}px`).toBeLessThanOrEqual(2);
 }
 await page.setViewportSize({width:390,height:850});
 const vision=page.getByRole("button",{name:"Для слабовидящих"});
 const base=await page.locator("html").evaluate(el=>getComputedStyle(el).fontSize);
 await vision.click();
 await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
 await expect(page.getByRole("button",{name:"Обычная версия"})).toHaveAttribute("aria-pressed","true");
 const large=await page.locator("html").evaluate(el=>getComputedStyle(el).fontSize);
 expect(parseFloat(large)).toBeGreaterThan(parseFloat(base)*1.1);
 await expect(page.getByRole("link",{name:"Доступная среда: условия посещения"})).toBeVisible();
 await page.reload({waitUntil:"networkidle"});
 await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
 await page.getByRole("link",{name:"Доступная среда: условия посещения"}).click();
 await expect(page).toHaveURL(/\/guide\/accessible-museum\/$/);
 await expect(page.locator("main")).toContainText("пандусы");
 await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
 await page.getByRole("button",{name:"Обычная версия"}).click();
 await expect(page.locator("html")).toHaveAttribute("data-vision-mode","off");
});

test("TZ-117/TZ-118: header has no critical/serious WCAG violations in enlarged-text mode", async ({page})=>{
 await page.goto("/",{waitUntil:"networkidle"});
 await page.getByRole("button",{name:"Для слабовидящих"}).click();
 await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
 const results=await new AxeBuilder({page}).include(".site-header").analyze();
 expect(results.violations.filter(v=>v.impact==="critical"||v.impact==="serious"),
   results.violations.map(v=>`${v.id} ${v.nodes.map(n=>n.target.join(",")).join(";")}`).join("\n"))
   .toEqual([]);
});
