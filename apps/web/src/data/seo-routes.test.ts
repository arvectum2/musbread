import test from "node:test";
import assert from "node:assert/strict";
import {publishedSitemapPaths,robotsRules,siteSeoApproved,sitemapUrls} from "./seo-routes.ts";
import type {MuseumSnapshot} from "./types";

const snapshot={schema_version:1,site:{name:"Тест",subtitle:"",description:""},
  events:[{slug:"open-day",title:"День",category:"Событие",date:"2026-11-03",excerpt:"",body:""}],
  entries:[
    {type:"page",slug:"exposition",title:"Экспозиция",h1:null,parent_slug:null,excerpt:"",body:"",seo_title:null,seo_description:null,sort_order:0},
    {type:"document",slug:"charter",title:"Устав",h1:null,parent_slug:null,excerpt:"",body:"",seo_title:null,seo_description:null,sort_order:0,
     translations:{en:{title:"Charter",excerpt:null,body:"",seo_title:null,seo_description:null}}},
  ],
} satisfies MuseumSnapshot;

test("TZ-191: every published route once incl. event index, nested guide and English only on reviewed translation",()=>{
 const routes=publishedSitemapPaths(snapshot,[{slug:"museum"}],[{href:"/guide/museum-history/"}],true);
 for(const required of ["/","/events/","/events/open-day/","/news/","/documents/charter/",
   "/museum/exposition/","/en/documents/charter/","/guide/museum/","/guide/museum-history/"])
  assert.ok(routes.includes(required),required);
 assert.ok(!routes.includes("/en/museum/exposition/"));
 assert.equal(routes.length,new Set(routes).size);
 assert.deepEqual(routes,[...routes].sort((a,b)=>a.localeCompare(b,"en")));
 assert.equal(publishedSitemapPaths(snapshot,[],[],false).some(p=>p.startsWith('/guide/')),false);
});

test("TZ-192: sitemap and robots never permit indexing unless explicit site-approved flag",()=>{
 const routes=publishedSitemapPaths(snapshot,[],[],false);
 assert.equal(siteSeoApproved(undefined),false);
 assert.equal(siteSeoApproved("TRUE"),false);
 assert.equal(siteSeoApproved("true"),true);
 assert.deepEqual(sitemapUrls(routes,false),[]);
 assert.equal(robotsRules(false).rules[0].disallow,"/");
 assert.equal(robotsRules(false).sitemap,undefined);
 assert.equal(robotsRules(true).rules[0].allow,"/");
 assert.equal(robotsRules(true).sitemap,"https://musbread.ru/sitemap.xml");
 assert.ok(sitemapUrls(routes,true).every(r=>r.url.startsWith("https://musbread.ru/")));
 assert.throws(()=>sitemapUrls(routes,true,"https://unapproved.test"));
});

test("Sitemap rejects out-of-policy paths from unverified data",()=>{
 const tampered={...snapshot,events:[{...snapshot.events[0],slug:"../cms-secret"}]};
 assert.throws(()=>publishedSitemapPaths(tampered,[],[],false));
});
