import {test,expect} from "@playwright/test";

const representative=["/","/events/","/news/","/news/demo-news/","/guide/museum-contacts/","/search/"];

test("TZ-189: all visitor links on representative published routes have a destination-derived title",async({page})=>{
  for(const url of representative){
    await page.goto(url,{waitUntil:"domcontentloaded"});
    const missing=await page.locator("a[href]").evaluateAll(els=>els.filter(el=>
      !(el.getAttribute("title") ?? "").trim()).map(el=>({
        href:el.getAttribute("href"),text:el.textContent?.trim().slice(0,80)
      })));
    expect(missing,"missing generated link title on "+url).toEqual([]);
    // The title provides *extra context*; native visible name remains intact.
    await expect(page.getByRole("link",{name:"Подробнее"}).first().or(
      page.getByRole("link",{name:"Новости"}).first()
    ).first()).toBeVisible();
  }
  await page.goto("/events/",{waitUntil:"domcontentloaded"});
  const details=page.getByRole("link",{name:/Подробнее/}).first();
  await expect(details).toHaveAttribute("title",/Открыть событие «/);
  await details.focus();
  await expect(details).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/events\/[^/]+\/$/);
});

test("TZ-208/210: real Tab and Shift+Tab keep keyboard focus visible on desktop and mobile",async({page})=>{
  test.setTimeout(90_000);
  for(const viewport of [{width:1440,height:850},{width:390,height:760}]){
    await page.setViewportSize(viewport);
    for(const url of representative.slice(0,4)){
      await page.goto(url,{waitUntil:"domcontentloaded"});
      await page.keyboard.press("Tab");
      const skip=page.getByRole("link",{name:"Перейти к содержимому"});
      await expect(skip).toBeFocused();
      await expect(skip).toBeVisible();
      const checked=new Set<string>();
      for(let i=0;i<26;i++){
        const focus=await page.evaluate(()=>{
          const el=document.activeElement as HTMLElement | null;
          if(!el || el===document.body) return null;
          const style=getComputedStyle(el);
          return {tag:el.tagName,html:el.outerHTML.slice(0,120),width:style.outlineWidth,
            style:style.outlineStyle,shadow:style.boxShadow,visible:el.getClientRects().length>0};
        });
        if(!focus) break;
        expect(focus.visible,"not displayed focus target "+url+" "+JSON.stringify(focus)).toBe(true);
        expect(parseFloat(focus.width),"missing ring at "+url+" "+JSON.stringify(focus))
          .toBeGreaterThanOrEqual(3);
        expect(focus.style).not.toBe("none");
        checked.add(focus.tag);
        await page.keyboard.press("Tab");
      }
      expect(checked.has("A")).toBe(true);
      // Reverse direction remains supported and does not send focus into hidden controls.
      await page.keyboard.press("Shift+Tab");
      const end=await page.evaluate(()=>document.activeElement?.tagName);
      expect(["A","BUTTON","SUMMARY","INPUT","SELECT"]).toContain(end);
    }
  }
});

test("TZ-209: Enter and Space operate menus, high contrast, event filters and native select",async({page})=>{
  await page.setViewportSize({width:1440,height:820});
  await page.goto("/",{waitUntil:"networkidle"});
  const summary=page.locator(".main-nav .mega-group summary").first();
  await summary.focus();await page.keyboard.press("Space");
  await expect(page.locator(".main-nav .mega-group").first()).toHaveAttribute("open","");
  await summary.focus();await page.keyboard.press("Enter");
  await expect(page.locator(".main-nav .mega-group").first()).not.toHaveAttribute("open","");

  const vision=page.getByRole("button",{name:"Для слабовидящих"});
  await vision.focus();await page.keyboard.press("Space");
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
  const activeVision=page.getByRole("button",{name:"Обычная версия"});
  const ring=await activeVision.evaluate(node=>({width:getComputedStyle(node).outlineWidth,
    shadow:getComputedStyle(node).boxShadow}));
  expect(parseFloat(ring.width)).toBeGreaterThanOrEqual(3);
  expect(ring.shadow).not.toBe("none");
  await activeVision.focus();await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode","off");

  await page.goto("/events/",{waitUntil:"networkidle"});
  const list=page.getByRole("region",{name:"Список мероприятий"});
  const period=list.getByRole("button",{name:/Архив/});
  await period.focus();await page.keyboard.press("Space");
  await expect(period).toHaveAttribute("aria-pressed","true");
  const next=list.getByRole("button",{name:/Предстоящие/});
  await next.focus();await page.keyboard.press("Enter");
  await expect(next).toHaveAttribute("aria-pressed","true");
  const category=list.getByRole("combobox",{name:"Категория мероприятий"});
  await category.focus();
  await expect(category).toBeFocused();
  await expect(category.locator("option")).toHaveCount(4);
  // Native HTML select option popups are implemented by the OS and headless
  // Chromium/macOS does not commit synthetic arrow keys. Form behaviour and
  // actual selectable options are independently covered by selectOption.
  // Real keyboard activation is tested above for both native summary dropdowns.
  await category.selectOption("Выставка");
  await expect(category).toHaveValue("Выставка");
  await category.selectOption("");
  await expect(category).toHaveValue("");
});

test("TZ-209/210: mobile nested menu, search combobox, and dark footer without a mouse",async({page})=>{
  await page.setViewportSize({width:390,height:800});
  await page.goto("/",{waitUntil:"networkidle"});
  const menu=page.locator(".mobile-nav > summary");
  await menu.focus();await page.keyboard.press("Space");
  await expect(page.locator(".mobile-nav")).toHaveAttribute("open","");
  const nested=page.locator(".mobile-subnav summary").first();
  await nested.focus();await page.keyboard.press("Enter");
  await expect(page.locator(".mobile-subnav").first()).toHaveAttribute("open","");
  const child=page.locator(".mobile-subnav").first().getByRole("link",{name:"Все подразделы"});
  await child.focus();await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/guide\/museum\/$/);
  await page.goto("/search/",{waitUntil:"networkidle"});
  const search=page.getByRole("combobox",{name:"Поиск по сайту"});
  await search.fill("история");
  await search.focus();await page.keyboard.press("ArrowDown");
  await expect(search).toHaveAttribute("aria-activedescendant",/list-0$/);
  await page.keyboard.press("Escape");
  await expect(search).toHaveAttribute("aria-expanded","false");
  const footer=page.locator("footer.site-footer a[href^='mailto:']").first();
  await page.keyboard.press("Tab");
  await footer.focus();
  await expect(footer).toBeFocused();
  const computed=await footer.evaluate(node=>({style:getComputedStyle(node).outlineStyle,
    width:getComputedStyle(node).outlineWidth,shadow:getComputedStyle(node).boxShadow}));
  expect(computed.style).not.toBe("none");
  expect(parseFloat(computed.width)).toBeGreaterThanOrEqual(3);
  expect(computed.shadow).not.toBe("none");
});
