import {test,expect} from "@playwright/test";

/** TZ-251/260: objective layout measurements, not final customer design UAT. */
const paths=["/","/search/","/events/","/news/","/guide/museum/","/guide/museum-contacts/","/guide/museum-documents/"];
test("TZ-251/260: representative routes have consistent gutters and no overlapping regions",async({page})=>{
  test.setTimeout(120_000);
  for(const width of [320,390,768,1024,1440,1920]){
    await page.setViewportSize({width,height:900});
    for(const url of paths){
      await page.goto(url,{waitUntil:"domcontentloaded"});
      await expect(page.locator("header.site-header")).toHaveCount(1);
      await expect(page.locator("main")).toHaveCount(1);
      await expect(page.locator("footer.site-footer")).toHaveCount(1);
      const sizes=await page.locator("main").evaluate(main=>{
        const block=main.querySelector(".section, .hero, article.section")!;
        const rect=block.getBoundingClientRect();
        const style=getComputedStyle(block);
        const pageWidth=document.documentElement.clientWidth;
        const footer=document.querySelector("footer.site-footer")!.getBoundingClientRect();
        return {
          left:rect.left,right:pageWidth-rect.right,
          paddingLeft:parseFloat(style.paddingLeft),
          paddingRight:parseFloat(style.paddingRight),
          footerGap:footer.top-main.getBoundingClientRect().bottom,
          overflow:document.documentElement.scrollWidth-pageWidth,
        };
      });
      expect(sizes.overflow,url+" at "+width+"px overflow").toBeLessThanOrEqual(2);
      expect(sizes.paddingLeft,url+" at "+width+"px left gutter").toBeGreaterThanOrEqual(12);
      expect(sizes.paddingRight,url+" at "+width+"px right gutter").toBeGreaterThanOrEqual(12);
      expect(Math.abs(sizes.paddingLeft-sizes.paddingRight),url+" at "+width+"px symmetric padding").toBeLessThanOrEqual(2);
      expect(sizes.footerGap,url+" at "+width+"px footer overlap").toBeGreaterThanOrEqual(-2);
    }
  }
});
test("TZ-261: sidebar is optional; flat/reference pages are not cluttered",async({page})=>{
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});
    await page.goto("/guide/museum-contacts/",{waitUntil:"domcontentloaded"});
    await expect(page.locator("article.guide-page .guide-sidebar")).toHaveCount(0);
    await expect(page.locator("article.guide-page .guide-primary")).toHaveCount(1);
    await expect(page.locator("article.guide-page .guide-content-single")).toHaveCount(1);
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(2);
  }
});
