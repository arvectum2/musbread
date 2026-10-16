import { expect,test } from "@playwright/test";

test("TZ-125/TZ-138: footer contact facts and contacts route with external map lookup",async({page})=>{
 await page.goto("/guide/museum-contacts/",{waitUntil:"networkidle"});
 const main=page.locator("main");
 await expect(main.getByRole("heading",{name:"Контакты"})).toBeVisible();
 await expect(main).toContainText("Михайлова, д. 2");
 await expect(main.getByRole("link",{name:"musbread@cult.gugov.spb.ru"})).toHaveAttribute("href","mailto:musbread@cult.gugov.spb.ru");
 const map=main.getByRole("link",{name:/Найти адрес на карте/});
 await expect(map).toHaveAttribute("href",/^https:\/\/yandex\.ru\/maps\/\?text=/);
 await expect(map).toHaveAttribute("rel",/noopener noreferrer/);
 await expect(main.getByRole("link",{name:"Условия доступности музея"})).toHaveAttribute("href","/guide/accessible-museum/");
 const footer=page.locator(".site-footer");
 for(const fragment of ["195009","294-50-82","10:00–18:00","Вторник"]){await expect(footer).toContainText(fragment)}
 await expect(footer.getByRole("link",{name:/Политика конфиденциальности/})).toHaveAttribute("href",/^https:\/\/muzei-xleb\.ru\//);
});

test("TZ-118/TZ-139: visit-planning and accessible-information pages link to official source",async({page})=>{
 await page.goto("/guide/plan-visit/");
 await expect(page.getByRole("heading",{name:"Как добраться"})).toBeVisible();
 await expect(page.getByRole("link",{name:"Условия доступности музея"})).toBeVisible();
 await page.goto("/guide/accessible-museum/");
 await expect(page.locator("main")).toContainText("пандусы и подъёмник");
 await expect(page.locator("main").getByRole("link",{name:/Актуальные сведения о доступности/})).toHaveAttribute("href",/^https:\/\/muzei-xleb\.ru\//);
});

test("TZ-173/TZ-174: sticky menu stays visible after scroll and submenu accessible by keyboard",async({page})=>{
 await page.goto("/",{waitUntil:"networkidle"});
 const header=page.locator(".site-header");
 await page.evaluate(()=>window.scrollTo(0,950));
 await expect.poll(()=>header.evaluate(el=>Math.abs(el.getBoundingClientRect().top))).toBeLessThan(2);
 const menu=page.getByRole("navigation",{name:"Основное меню"});
 const museum=menu.locator(".mega-group").first();
 await museum.locator("summary").focus();
 await page.keyboard.press("Enter");
 await expect(museum).toHaveAttribute("open","");
 await expect(museum.getByRole("link",{name:"История музея",exact:true})).toBeVisible();
 await museum.getByRole("link",{name:"История музея",exact:true}).focus();
 await page.keyboard.press("Enter");
 await expect(page).toHaveURL(/\/guide\/museum-history\/$/);
});
