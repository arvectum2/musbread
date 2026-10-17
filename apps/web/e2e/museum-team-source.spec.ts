import {expect,test} from "@playwright/test";
test("only official old-site team roles, with attribution and approval warning",async({page})=>{
 await page.goto("/guide/museum-team/");
 const team=page.getByRole("region",{name:"Руководство и администрация музея"});
 await expect(team).toBeVisible();await expect(team.locator("li")).toHaveCount(5);
 await expect(team).toContainText("Елизавета Вилорьевна Тапакова-Боярская");
 await expect(team).toContainText("Оксана Владимировна Кутовая");
 await expect(team).toContainText("Используется опубликованная редакция");
 await expect(team.getByRole("link",{name:/Первоисточник/})).toHaveAttribute("href","https://muzei-xleb.ru/administraciya");
 await expect(team.locator("a[href^='tel:']")).toHaveCount(5);
});
test("administration readable at 320px with keyboard focus",async({page})=>{
 await page.setViewportSize({width:320,height:700});await page.goto("/guide/museum-team/");
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
 const source=page.getByRole("link",{name:/Первоисточник/});
 await source.focus();await expect(source).toBeFocused();
});
