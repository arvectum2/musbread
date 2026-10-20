import assert from "node:assert/strict";
import test from "node:test";
import {visibleGuideSectionEntries,shouldShowGuideReferenceBody} from "./guide-page-rules.ts";

const entries=[
 {type:"page",slug:"museum-exposition",title:"Self"},
 {type:"exhibition",slug:"gallery-source",title:"Existing original"},
 {type:"news",slug:"unrelated",title:"CMS article"},
 {type:"page",slug:"museum-exposition",title:"Duplicate revision"},
 {type:"page",slug:"other-section",title:"Other CMS section"},
];

test("source-backed exhibitions suppress originals and self; retained ordering and input unchanged",()=>{
 const original=structuredClone(entries);
 const picked=visibleGuideSectionEntries("museum-exposition",entries,new Set(["gallery-source"]));
 assert.deepEqual(picked.map(item=>item.slug),["unrelated","other-section"]);
 assert.deepEqual(entries,original);
});

test("a CMS page in its own guide slug is never listed as a second entry",()=>{
 assert.deepEqual(visibleGuideSectionEntries("science-materials",
   [{type:"page",slug:"science-materials"},{type:"page",slug:"another"}],
   new Set()).map(x=>x.slug),["another"]);
});

test("source verified program and published revision remain separate when slugs differ",()=>{
 const result=visibleGuideSectionEntries("children-interactive",
   [{type:"excursion",slug:"museum-program"},{type:"excursion",slug:"museum-editor-addition"}],
   new Set(["museum-program"]));
 assert.deepEqual(result.map(item=>item.slug),["museum-editor-addition"]);
});

test("only official sections with no editor revision suppress duplicate source body",()=>{
 const input={slug:"museum-exposition",hasBody:true,hasCmsPage:false,
   sourceProgramsCategory:false,sourceExhibitionCategory:false};
 assert.equal(shouldShowGuideReferenceBody(input),false);
 assert.equal(shouldShowGuideReferenceBody({...input,hasCmsPage:true}),true);
 assert.equal(shouldShowGuideReferenceBody({...input,slug:"excursion-thematic",sourceProgramsCategory:true}),false);
 assert.equal(shouldShowGuideReferenceBody({...input,slug:"exhibitions-current",sourceExhibitionCategory:true}),false);
 assert.equal(shouldShowGuideReferenceBody({...input,slug:"museum-history"}),true);
});

test("legal/contact/cookie sections and empty bodies are not duplicated",()=>{
 const base={slug:"museum-team",hasBody:true,hasCmsPage:true,
   sourceProgramsCategory:false,sourceExhibitionCategory:false};
 for(const slug of ["museum-team","museum-contacts","museum-cookie"])
   assert.equal(shouldShowGuideReferenceBody({...base,slug}),false,slug);
 assert.equal(shouldShowGuideReferenceBody({...base,slug:"museum-history",hasBody:false}),false);
});
