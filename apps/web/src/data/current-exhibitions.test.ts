import {test} from "node:test";
import {strict as assert} from "node:assert";
import {currentlyRunningExhibitions,futureExhibitions} from "./current-exhibitions.ts";
import type {MuseumEvent} from "./types.ts";
const e=(slug:string,category:string,date:string,ends_on?:string):MuseumEvent=>
  ({slug,category,date,ends_on,title:slug,body:"",excerpt:""});
test("current exhibitions require started and not ended, including multiday ending today",()=>{
 const events=[
  e("old","Выставка","2026-10-01","2026-10-10"),
  e("current","Выставка","2026-10-05","2026-10-20"),
  e("one-day","Выставка","2026-10-17"),
  e("future","Выставка","2026-11-19","2026-11-30"),
  e("lecture","Лекция","2026-10-17","2026-10-20"),
 ];
 assert.deepEqual(currentlyRunningExhibitions(events,"2026-10-17").map(x=>x.slug),["current","one-day"]);
 assert.deepEqual(futureExhibitions(events,"2026-10-17").map(x=>x.slug),["future"]);
 assert.deepEqual(currentlyRunningExhibitions(events,"2026-10-20").map(x=>x.slug),["current"]);
 assert.deepEqual(currentlyRunningExhibitions(events,"2026-10-21").map(x=>x.slug),[]);
});
test("bad dates, archives, other types and absence do not imply current exhibition",()=>{
 assert.deepEqual(currentlyRunningExhibitions([
  e("bad","Выставка","2026-13-01"),e("past","Выставка","2025-01-01"),
  e("workshop","Мастер-класс","2026-10-17"),
 ],"2026-10-17"),[]);
 assert.deepEqual(currentlyRunningExhibitions([],"2026-10-17"),[]);
 assert.deepEqual(currentlyRunningExhibitions([e("a","Выставка","2026-10-17")],"wrong-date"),[]);
});
