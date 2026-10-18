import {expect,test} from "@playwright/test";

test("original public museum PDF and DOCX URLs stay alive after changing DNS",async({page})=>{
  const cases=[
    ["/sites/default/files/page/20240117170312-uchetnaya_politika.pdf","application/pdf","%PDF"],
    ["/sites/default/files/page/20260203104919-1.pdf","application/pdf","%PDF"],
    ["/sites/default/files/page/20260203114639-ustav_2011.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document","PK"],
    ["/sites/default/files/page/20240419153512-prikaz_pravila_poseshcheniya_organizovannymi_gruppami_ekskursiy.pdf","application/pdf","%PDF"],
    ["/sites/default/files/page/20251203120738-informaciya_dlya_dariteley.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document","PK"],
  ] as const;
  for(const [originalPath,type,signature] of cases){
    const res=await page.request.get(originalPath);
    expect(res.status(),`Old museum public file must serve: ${originalPath}`).toBe(200);
    expect(res.headers()["content-type"]).toContain(type);
    expect((await res.body()).subarray(0,signature.length).toString()).toBe(signature);
  }
});
