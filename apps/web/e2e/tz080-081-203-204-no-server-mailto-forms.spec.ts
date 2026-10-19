import {expect,test} from '@playwright/test';
const museumMail='musbread@cult.gugov.spb.ru';

test('TZ-080/203: real feedback form composes email ONLY on visitor click; no server submission',async({page})=>{
 await page.goto('/forms/feedback/');
 await expect(page.getByRole('heading',{name:'Обратная связь'})).toBeVisible();
 await expect(page.getByRole('link',{name:/Открыть письмо в почтовой программе/})).toHaveCount(0);
 await page.getByLabel('Ваше имя').fill('QA без реальных ПДн');
 await page.getByLabel('Ваш вопрос').fill('Тестовый вопрос о времени работы');
 await page.getByRole('button',{name:'Сформировать письмо'}).click();
 const mail=page.getByRole('link',{name:/Открыть письмо в почтовой программе/});
 await expect(mail).toHaveAttribute('href',new RegExp('^mailto:'+museumMail.replaceAll('.','\\.')+'\\?'));
 const href=await mail.getAttribute('href');
 const body=new URL(href!).searchParams.get('body')||'';
 expect(body).toContain('Тестовый вопрос о времени работы');
 await expect(page.getByText(/Проверьте письмо и отправьте его самостоятельно/)).toBeVisible();
 await expect(page.locator('form')).toHaveAttribute('method','post');
 await page.getByLabel('Ваш вопрос').fill('Изменённый вопрос');
 await expect(mail).toHaveCount(0);
});

test('TZ-081/204: excursion request collects date and group and never confirms booking',async({page})=>{
 await page.goto('/forms/excursion/');
 await page.getByLabel('Ваше имя').fill('Тестовый заявитель');
 await page.getByLabel('Предпочтительная дата экскурсии').fill('2026-11-04');
 await page.getByLabel('Количество посетителей').fill('6');
 await page.getByLabel('Дополнительная информация').fill('Тест группы');
 await page.getByRole('button',{name:'Сформировать письмо'}).click();
 const mail=page.getByRole('link',{name:/Открыть письмо в почтовой программе/});
 await expect(mail).toHaveAttribute('href',new RegExp('^mailto:'+museumMail.replaceAll('.','\\.')+'\\?'));
 const body=new URL((await mail.getAttribute('href'))!).searchParams.get('body')||'';
 expect(body).toContain('2026-11-04');expect(body).toContain('Количество посетителей: 6');
 await expect(page.getByText(/Дата и время экскурсии ещё не подтверждены музеем/)).toBeVisible();
 await expect(page.getByRole('link',{name:/Политика обработки персональных данных музея/})).toHaveAttribute('href','/guide/museum-privacy/');
});

test('TZ-080/081: entry points exist on museum source pages, without new menu or visitor cabinet',async({page})=>{
 await page.goto('/guide/museum-feedback/');
 await expect(page.getByRole('link',{name:/Написать в музей через форму/})).toHaveAttribute('href','/forms/feedback/');
 await page.goto('/guide/excursion-overview/');
 await expect(page.getByRole('link',{name:/Отправить запрос на экскурсию/})).toHaveAttribute('href','/forms/excursion/');
 await page.goto('/');
 await expect(page.locator('footer.site-footer a[href="/forms/feedback/"]')).toHaveCount(1);
 await expect(page.locator('footer.site-footer a[href="/forms/excursion/"]')).toHaveCount(1);
});

test('TZ-080/081 security: with JavaScript disabled public forms cannot submit names or messages to static server',async({browser})=>{
 const context=await browser.newContext({javaScriptEnabled:false});
 const page=await context.newPage();
 for(const kind of ['feedback','excursion']){
  await page.goto('http://127.0.0.1:18765/forms/'+kind+'/');
  await expect(page.locator('form')).toHaveAttribute('method','post');
  await expect(page.locator('form fieldset')).toHaveAttribute('disabled','');
  await expect(page.getByRole('button',{name:'Сформировать письмо'})).toBeDisabled();
 }
 await context.close();
});
