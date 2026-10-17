import assert from "node:assert/strict";
import test from "node:test";
import {isAgendaSection,publishedEventsForAgendaSection} from "./agenda-sections.ts";
import type {MuseumEvent} from "./types.ts";
const demo=(slug:string,category:string,section_slug?:string):MuseumEvent =>
 ({slug,title:slug,date:"2026-11-11",category,section_slug,body:"Demo",excerpt:"Demo"});
const cases=[
 demo("plain-excursion","Экскурсия"),
 demo("child-workshop","Мастер-класс","children-workshops"),
 demo("generic-workshop","Мастер-класс"),
 demo("lecture","Лекция"),
 demo("festival","Фестиваль"),
 demo("exhibition","Выставка"),
 demo("child-tour","Детская экскурсия"),
 demo("wrong-substring","Не фестиваль"),
 demo("case-sensitive","фестиваль"),
 demo("explicit-meeting","Мероприятие","agenda-meetings"),
];

test("agenda pages filter ONLY approved exact category/section, not guessed substring",()=>{
 assert.deepEqual(publishedEventsForAgendaSection(cases,"agenda-meetings").map(x=>x.slug),["lecture","explicit-meeting"]);
 assert.deepEqual(publishedEventsForAgendaSection(cases,"agenda-festivals").map(x=>x.slug),["festival"]);
 assert.deepEqual(publishedEventsForAgendaSection(cases,"agenda-workshops").map(x=>x.slug),["child-workshop","generic-workshop"]);
 assert.deepEqual(publishedEventsForAgendaSection(cases,"agenda-children").map(x=>x.slug),["child-workshop","child-tour"]);
 assert.deepEqual(publishedEventsForAgendaSection(cases,"agenda-exhibitions").map(x=>x.slug),["exhibition"]);
 assert.ok(!publishedEventsForAgendaSection(cases,"agenda-children").some(e=>e.slug==="plain-excursion"));
 assert.ok(isAgendaSection("agenda-archive"));
 assert.ok(!isAgendaSection("agenda-something-else"));
});

test("all sections return empty for no real museum events; no fake fallback entries",()=>{
 for (const slug of ["agenda-children","agenda-meetings","agenda-festivals","agenda-workshops"] as const)
  assert.deepEqual(publishedEventsForAgendaSection([],slug),[]);
 assert.deepEqual(publishedEventsForAgendaSection(cases,"agenda-archive"),cases);
 assert.deepEqual(publishedEventsForAgendaSection([], "agenda-archive"),[]);
});
