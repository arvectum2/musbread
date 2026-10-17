import {expect,test} from "@playwright/test";

/** Technical UI acceptance only. No unapproved museum colours or artwork. */
const routes=[
 "/", "/news/", "/events/", "/search/", "/guide/museum/",
 "/guide/museum-media/", "/guide/museum-contacts/",
 "/guide/museum-documents/"
];
test("TZ-251/260: same content baseline for header, main and footer on 8 routes × 6 widths",async({page})=>{
 test.setTimeout(125_000);
 for (const width of [320,390,768,1024,1440,1920]){
  await page.setViewportSize({width,height:920});
  for(const url of routes){
   await page.goto(url,{waitUntil:"domcontentloaded"});
   const v=await page.evaluate(()=>{
    const header=document.querySelector<HTMLElement>(".header-inner")!;
    const section=document.querySelector<HTMLElement>("main > .section, main > article.section, main > .hero")!;
    const footer=document.querySelector<HTMLElement>(".site-footer")!;
    const footerColumn=footer.querySelector<HTMLElement>(".footer-info")!;
    const headerBrand=header.querySelector<HTMLElement>(".wordmark")!;
    const first=section.firstElementChild as HTMLElement;
    const hp=parseFloat(getComputedStyle(header).paddingLeft);
    const mp=parseFloat(getComputedStyle(section).paddingLeft);
    const pageWidth=document.documentElement.clientWidth;
    return {
      headerX:headerBrand.getBoundingClientRect().left,
      mainX:first.getBoundingClientRect().left,
      footerX:footerColumn.getBoundingClientRect().left,
      hPad:hp,mPad:mp,
      hRight:parseFloat(getComputedStyle(header).paddingRight),
      mRight:parseFloat(getComputedStyle(section).paddingRight),
      shellRatio:section.getBoundingClientRect().width/pageWidth,
      overflow:document.documentElement.scrollWidth-pageWidth,
      sectionTop:section.getBoundingClientRect().top,
      footerTop:footer.getBoundingClientRect().top,
      sectionBottom:section.getBoundingClientRect().bottom,
    };
   });
   const msg=url+" / "+width+"px";
   expect(v.hPad,msg+" header left gutter").toBeGreaterThanOrEqual(12);
   expect(v.mPad,msg+" main left gutter").toBeGreaterThanOrEqual(12);
   expect(Math.abs(v.hPad-v.mPad),msg+" uniform gutters").toBeLessThanOrEqual(1);
   expect(Math.abs(v.hPad-v.hRight),msg+" header symmetric").toBeLessThanOrEqual(1);
   expect(Math.abs(v.mPad-v.mRight),msg+" main symmetric").toBeLessThanOrEqual(1);
   expect(Math.abs(v.headerX-v.mainX),msg+" header vs main baseline").toBeLessThanOrEqual(1.6);
   expect(Math.abs(v.footerX-v.mainX),msg+" footer vs main baseline").toBeLessThanOrEqual(1.6);
   expect(v.shellRatio,msg+" >=80% page shell").toBeGreaterThanOrEqual(.8);
   expect(v.overflow,msg+" horizontal overflow").toBeLessThanOrEqual(2);
   expect(v.footerTop,msg+" footer below content").toBeGreaterThanOrEqual(v.sectionBottom-2);
  }
 }
});
test("TZ-242: reduced-motion preference disables decorative transitions and smooth scrolling",async({page})=>{
 await page.emulateMedia({reducedMotion:"reduce"});
 await page.goto("/",{waitUntil:"domcontentloaded"});
 const data=await page.evaluate(()=>{
  const a=document.querySelector(".primary-button") ?? document.querySelector("a")!;
  return {
   scroll:getComputedStyle(document.documentElement).scrollBehavior,
   transition:getComputedStyle(a).transitionDuration,
   animation:getComputedStyle(a).animationDuration,
   iframeCount:document.querySelectorAll("iframe,video[autoplay],audio[autoplay]").length,
  };
 });
 expect(data.scroll).toBe("auto");
 expect(data.transition).toMatch(/(?:0s|1e-05s|0\.00001s)/);
 expect(data.iframeCount).toBe(0);
});
