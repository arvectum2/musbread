import test from "node:test";
import assert from "node:assert/strict";
import {museumAdministration, museumAdministrationSource, museumAdministrationCheckedAt} from "./museum-team.ts";
test("directory comes from the existing museum administration page",()=>{
 assert.equal(museumAdministration.length,5);
 assert.equal(museumAdministrationSource,"https://muzei-xleb.ru/administraciya");
 assert.equal(museumAdministrationCheckedAt,"17.10.2026");
 assert.equal(new Set(museumAdministration.map(x=>x.role)).size,5);
 for(const p of museumAdministration){
  assert.ok(p.name.includes(" ")); assert.ok(p.role);
  assert.match(p.phoneHref,/^tel:\+781229450(82|91)$/);
  assert.equal(p.phoneHref.replace(/[^\d]/g,""),p.phone.replace(/[^\d]/g,""));
 }
});
