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
  await page.goto("/guide/"+route+"/");
  const category=page.getByRole("region",{name:"Мероприятия раздела: "+name});
  await expect(category).toBeVisible();
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
