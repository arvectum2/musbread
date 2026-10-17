import {expect,test} from "@playwright/test";

test("museum document hub follows Russian and St Petersburg museums' grouped-source pattern", async({page})=>{
 await page.goto('/guide/museum-documents/',{waitUntil:'networkidle'});
 const hub=page.getByRole('region',{name:'Официальные документы музея'});
 await expect(hub).toBeVisible();
 await expect(hub).toContainText('Учредительные документы');
 await expect(hub).toContainText('Политики обработки персональных данных');
 await expect(hub).toContainText('Правила посещения и билеты');
 await expect(hub).toContainText('Документы и сведения о доступности');
 await expect(hub).toContainText('Устав музея');
 await expect(hub).toContainText('Положение о порядке приобретения и возврата билетов');
 await expect(hub).toContainText('перед запуском нового сайта музей должен подтвердить актуальность редакций');
 await expect(hub.locator('a[href^="https://muzei-xleb.ru/"]')).toHaveCount(21);
 for(const anchor of await hub.locator('a[href^="https://muzei-xleb.ru/"]').all()){
   await expect(anchor).toHaveAttribute('target','_blank');
   await expect(anchor).toHaveAttribute('rel',/noopener noreferrer/);
 }
 await expect(page.getByRole('button',{name:/Я согласен|Принять cookie/})).toHaveCount(0);
 await expect(page.locator('form[action*="consent"]')).toHaveCount(0);
});

test('privacy and refund pages show the proper museum documents without copying policies',async({page})=>{
 await page.goto('/guide/museum-privacy/');
 const privacy=page.getByRole('region',{name:'Официальные документы музея'});
 await expect(privacy.locator('.official-documents-group')).toHaveCount(1);
 await expect(privacy).toContainText('Политика по обработке и защите персональных данных');
 await expect(privacy).not.toContainText('Положение о порядке приобретения и возврата');
 await page.goto('/guide/ticket-refunds/');
 const ticket=page.getByRole('region',{name:'Официальные документы музея'});
 await expect(ticket).toContainText('Правила посещения музея');
 await expect(ticket).toContainText('Положение о порядке приобретения и возврата билетов');
 await expect(ticket).not.toContainText('Устав музея');
});

test('official source hub has no horizontal overflow at 320px and supports keyboard focus',async({page})=>{
 await page.setViewportSize({width:320,height:750});
 await page.goto('/guide/museum-documents/');
 const hub=page.getByRole('region',{name:'Официальные документы музея'});
 await expect(hub).toBeVisible();
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
 expect(overflow).toBeLessThanOrEqual(2);
 const link=hub.getByRole('link',{name:/Устав музея/});
 await link.focus();
 await expect(link).toBeFocused();
 await page.keyboard.press('Enter');
 // Opens in another tab; remain on the museum's locally served prototype.
 await expect(page).toHaveURL(/\/guide\/museum-documents\/$/);
});
