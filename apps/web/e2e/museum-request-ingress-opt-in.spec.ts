import {expect,test} from '@playwright/test';

test.skip(process.env.MUSEUM_REQUEST_E2E_OPT_IN!=='1',
    'Runs only against an explicitly enabled synthetic static build');

test('private data is POSTed only after consent; failed delivery retries same ID',async({page})=>{
 const sent: Array<Record<string,unknown>>=[];
 let attempts=0;
 await page.route('https://requests.musbread.ru/v1/requests',async route=>{
  const req=route.request();
  if(req.method()==='OPTIONS'){
   await route.fulfill({status:204,headers:{
    'Access-Control-Allow-Origin':'http://127.0.0.1:18766',
    'Access-Control-Allow-Methods':'POST, OPTIONS',
    'Access-Control-Allow-Headers':'Content-Type'}});return;
  }
  sent.push(req.postDataJSON() as Record<string,unknown>);
  attempts++;
  await route.fulfill({status:attempts===1?503:202,
   contentType:'application/json',
   headers:{'Access-Control-Allow-Origin':'http://127.0.0.1:18766'},
   body:attempts===1?'{"error":"unavailable"}':
     '{"status":"received","request_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'});
 });
 await page.goto('/forms/feedback/');
 await expect(page.getByRole('button',{name:'Отправить обращение'})).toBeVisible();
 await page.getByLabel('Ваше имя').fill('Тестовый посетитель');
 await page.getByLabel('Электронная почта для ответа').fill('synthetic@example.org');
 await page.getByLabel('Ваш вопрос').fill('Только синтетический тест');
 const button=page.getByRole('button',{name:'Отправить обращение'});
 await button.click();
 expect(sent).toHaveLength(0); // no consent => never leave the browser
 await page.getByRole('checkbox').check();
 await button.click();
 await expect(page.getByText(/Не удалось подтвердить доставку/)).toBeVisible();
 await button.click();
 await expect(page.getByText(/Обращение получено для обработки/)).toBeVisible();
 expect(sent).toHaveLength(2);
 expect(sent[0].email).toBe('synthetic@example.org');
 expect(sent[0].client_id).toMatch(/^[a-f0-9]{32}$/);
 expect(sent[0].client_id).toBe(sent[1].client_id);
 expect(sent[0].consent).toBe('test-v1');
 expect(sent[0].kind).toBe('feedback');
});
