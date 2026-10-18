import {expect,test} from "@playwright/test";

test("TZ-140: visitor plan directly contains truthful museum mobility information",async({page})=>{
  await page.goto("/guide/plan-visit/");
  const panel=page.getByRole("region",{name:"Доступная среда при планировании визита"});
  await expect(panel).toBeVisible();
  for(const heading of [
    "Вход и помощь","Экспозиция и подъём","Туалет",
    "Для посетителей с нарушениями зрения",
    "Для посетителей с нарушениями слуха","Собака-проводник",
  ]){
    await expect(panel.getByRole("heading",{name:heading})).toBeVisible();
  }
  await expect(panel).toContainText("улицы Михайлова, 2");
  await expect(panel).toContainText("первого и второго этажей");
  await expect(panel).toContainText("отсутствие тактильной и визуальной информации");
  await expect(panel).toContainText("Музей просит заранее позвонить");
  await expect(panel.locator("a[href='tel:+78122945082']")).toHaveCount(1);
  await expect(panel.locator("a[href='https://muzei-xleb.ru/informaciya-dlya-mgn']")).toHaveCount(1);
});

test("TZ-144: full official accessibility source is readable and can be updated via CMS",async({page})=>{
  await page.goto("/guide/accessible-museum/");
  const source=page.getByRole("region",{name:"Содержание действующего сайта музея"});
  await expect(source).toContainText("Поднимитесь на выход");
  await expect(source).toContainText("тактильная карта водных систем");
  await expect(source).toContainText("собак");
  await expect(page.getByRole("region",{name:"Доступная среда при планировании визита"})).toContainText("пандусами");
  await expect(page.getByRole("link",{name:/Адрес, часы работы и план визита/})).toHaveAttribute("href","/guide/plan-visit/");
});

test("TZ-143: real museum Pushkin-card rules and ticketing operator are displayed",async({page})=>{
  await page.goto("/guide/pushkin-card/");
  const source=page.getByRole("region",{name:"Содержание действующего сайта музея"});
  await expect(source).toContainText("14 до 22 лет");
  await expect(source).toContainText("можно купить только онлайн");
  await expect(source.locator('a[href="https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba"]')).toHaveCount(1);
  await expect(page.locator("main")).not.toContainText("Сведения не найдены");
});

test("TZ-140: the mobility guidance fits small phones and retains links",async({page})=>{
  await page.setViewportSize({width:320,height:690});
  await page.goto("/guide/plan-visit/");
  const facts=page.locator(".visit-accessibility-fact");
  await expect(facts).toHaveCount(6);
  await expect(facts.last()).toBeVisible();
  const sizes=await page.evaluate(()=>({
    width:document.documentElement.clientWidth,
    content:document.documentElement.scrollWidth,
  }));
  expect(sizes.content).toBeLessThanOrEqual(sizes.width+1);
});
