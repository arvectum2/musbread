import assert from "node:assert/strict";
import test from "node:test";
import { guidePages, guideHref, LEGACY_BASE, legacyUrl, menuGroups, museumReference } from "./museum-reference.ts";

test("семь верхних категорий обязательны, slug всех страниц уникальны", () => {
  assert.equal(menuGroups.length, 7);
  assert.equal(new Set(guidePages.map((p) => p.slug)).size, guidePages.length);
  assert.ok(guidePages.length >= 40);
});

test("официальные контакты и билетная площадка — временные сведения со старого сайта", () => {
  assert.match(museumReference.address, /Михайлова/);
  assert.equal(museumReference.email, "musbread@cult.gugov.spb.ru");
  assert.equal(new URL(museumReference.ticketUrl).hostname, "vmuzey.com");
});

test("ссылки на старый сайт ограничены доменом музея", () => {
  for (const page of guidePages) {
    if (!page.legacyPath) continue;
    assert.equal(new URL(legacyUrl(page.legacyPath)).origin, LEGACY_BASE);
  }
});

test("новые разделы отличимы от подтверждённых на старом сайте", () => {
  assert.ok(guidePages.some((page) => page.tenderOnly));
  assert.ok(guidePages.some((page) => page.legacyPath));
  assert.ok(guidePages.every((page) => !page.tenderOnly || !page.legacyPath));
});

test("Пушкинская карта: существующий материал музея, а не выдуманный раздел", () => {
  for (const slug of ["pushkin-card", "children-pushkin-card", "exhibitions-pushkin-card"]) {
    const page = guidePages.find((item) => item.slug === slug);
    assert.ok(page, slug);
    assert.equal(page.legacyPath, "/pushkinskaya-karta");
    assert.equal(page.tenderOnly, undefined);
    assert.equal(legacyUrl(page.legacyPath), "https://muzei-xleb.ru/pushkinskaya-karta");
  }
});

test("TZ-075: известная афиша — единый маршрут; источник новостей не заменяется демо", () => {
  assert.equal(guideHref("agenda-events"), "/events/");
  assert.equal(guideHref("museum-contacts"), "/guide/museum-contacts/");
  assert.equal(guidePages.find((p) => p.slug === "agenda-events")?.href, "/events/");
  assert.equal(museumReference.newsUrl, "https://muzei-xleb.ru/novosty");
});
