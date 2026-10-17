import test from "node:test";
import assert from "node:assert/strict";
import {officialMuseumDocumentGroups,officialMuseumGroupsForPage,officialMuseumDocumentSources} from "./museum-official-documents.ts";

test("museum-owned file sources are HTTPS and correspond to verified old-site pages",()=>{
 assert.equal(officialMuseumDocumentGroups.length,5);
 let count=0;
 for(const group of officialMuseumDocumentGroups){
   assert.ok(group.title.trim().length>10);
   assert.ok(group.items.length>=2);
   assert.equal(new URL(group.source).origin,"https://muzei-xleb.ru");
   const ids=new Set<string>();
   for(const item of group.items){
     const url=new URL(item.url);
     assert.equal(url.origin,"https://muzei-xleb.ru");
     assert.equal(url.username,"");assert.equal(url.password,"");
     assert.equal(url.search,"");assert.equal(url.hash,"");
     if(item.format==="PDF")assert.ok(url.pathname.endsWith('.pdf'));
     else if(item.format==="DOCX")assert.ok(url.pathname.endsWith('.docx'));
     else assert.ok(!url.pathname.includes('/sites/default/files'));
     assert.ok(item.label.trim().length>=10);
     assert.ok(!ids.has(item.url));ids.add(item.url);count++;
   }
 }
 assert.ok(count>=16);
});

test("privacy, returns and accessibility show only actual museum sources, never invented legal copy",()=>{
 assert.equal(officialMuseumGroupsForPage("museum-privacy")[0].items.length,2);
 assert.ok(officialMuseumGroupsForPage("ticket-refunds").some(g=>g.items.some(item=>item.label.includes('возврата'))));
 assert.ok(officialMuseumGroupsForPage("accessible-museum")[0].items.some(item=>item.label.includes('маломобильных')));
 assert.deepEqual(officialMuseumGroupsForPage("unrelated"),[]);
 assert.equal(officialMuseumDocumentSources.privacy,'https://muzei-xleb.ru/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh');
});
