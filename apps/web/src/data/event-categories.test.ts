import {test} from "node:test";
import {strict as assert} from "node:assert";
import {eventCategories, eventsForCategory, eventsForPeriod} from "./event-archive.ts";
import type {MuseumEvent} from "./types.ts";

const events: MuseumEvent[]=[
 {slug:"e",title:"E",category:"Экскурсия",date:"2026-11-10",excerpt:"",body:""},
 {slug:"x",title:"X",category:"Выставка",date:"2026-11-11",excerpt:"",body:""},
 {slug:"m",title:"M",category:"Мастер-класс",date:"2026-11-12",excerpt:"",body:""},
 {slug:"old",title:"Old",category:"Выставка",date:"2026-10-10",excerpt:"",body:""},
];
test("categories taken from submitted CMS data; no invented taxonomy",()=>{
 assert.deepEqual(eventCategories(events),["Выставка","Мастер-класс","Экскурсия"]);
 assert.deepEqual(eventCategories([]),[]);
 assert.deepEqual(eventCategories([{...events[0],category:"  Экскурсия  "}]),["Экскурсия"]);
});
test("category filter only matches exact category, never substring of unrelated event",()=>{
 assert.deepEqual(eventsForCategory(events,"Выставка").map(e=>e.slug),["x","old"]);
 assert.equal(eventsForCategory(events,"Выстав").length,0);
 assert.equal(eventsForCategory(events,"").length,4);
});
test("category and archive compose, history does not disappear",()=>{
 const filtered=eventsForCategory(events,"Выставка");
 assert.deepEqual(eventsForPeriod(filtered,"2026-11-06","upcoming").map(e=>e.slug),["x"]);
 assert.deepEqual(eventsForPeriod(filtered,"2026-11-06","archive").map(e=>e.slug),["old"]);
});
