import assert from "node:assert/strict";
import test from "node:test";
import { eventsForPeriod, localCalendarDay, validCalendarDay } from "./event-archive.ts";
import type { MuseumEvent } from "./types";
const demo = (slug: string, date: string): MuseumEvent => ({ slug, date, category: "Экскурсия", title: slug, excerpt: "Demo", body: "Demo" });

test("published calendar dates: today still upcoming; yesterday is archived", () => {
  const events = [demo("tomorrow", "2026-11-06"), demo("today", "2026-11-05"), demo("yesterday", "2026-11-04")];
  assert.deepEqual(eventsForPeriod(events, "2026-11-05", "upcoming").map(e => e.slug), ["today", "tomorrow"]);
  assert.deepEqual(eventsForPeriod(events, "2026-11-05", "archive").map(e => e.slug), ["yesterday"]);
  assert.deepEqual(eventsForPeriod(events, "2026-11-05", "all").map(e => e.slug), ["yesterday", "today", "tomorrow"]);
  assert.deepEqual(events.map(e => e.slug), ["tomorrow", "today", "yesterday"], "sorting must never modify the published snapshot");
});

test("multi-day exhibition remains upcoming until its end day", () => {
  const exhibition: MuseumEvent = { ...demo("exhibition-week", "2026-11-01"), ends_on: "2026-11-19" };
  assert.deepEqual(eventsForPeriod([exhibition], "2026-11-18", "upcoming").map(e=>e.slug), ["exhibition-week"]);
  assert.deepEqual(eventsForPeriod([exhibition], "2026-11-19", "archive").map(e=>e.slug), []);
  assert.deepEqual(eventsForPeriod([exhibition], "2026-11-20", "archive").map(e=>e.slug), ["exhibition-week"]);
  assert.equal(eventsForPeriod([exhibition], "2026-11-20", "all").length, 1);
});

test("archived events sort newest first and same-day ties are stable", () => {
  const events = [demo("a", "2026-10-03"),demo("x", "2026-10-05"),demo("b", "2026-10-05")];
  assert.deepEqual(eventsForPeriod(events,"2026-10-06","archive").map(e => e.slug),["b","x","a"]);
});

test("date-only and missing dates never make a published event vanish", () => {
  const events = [demo("unknown", ""),demo("invalid", "2026-02-30"), demo("valid","2026-03-01")];
  assert.equal(validCalendarDay("2026-02-30"), false);
  assert.equal(validCalendarDay("2028-02-29"), true);
  assert.equal(validCalendarDay("2027-02-29"), false);
  assert.deepEqual(eventsForPeriod(events,"2026-04-01","archive").map(e => e.slug),["valid"]);
  assert.deepEqual(eventsForPeriod(events,"2026-04-01","upcoming").map(e => e.slug),["invalid","unknown"]);
  assert.equal(eventsForPeriod(events,"2026-04-01","all").length,3);
});

test("local calendar day respects visitor timezone instead of UTC day", () => {
  // Local helper uses the runtime's actual timezone, no environment assumptions.
  const date = new Date(2026,10,5,23,59);
  assert.equal(localCalendarDay(date),"2026-11-05");
  assert.equal(localCalendarDay(new Date(2026,10,6,0,1)),"2026-11-06");
});
