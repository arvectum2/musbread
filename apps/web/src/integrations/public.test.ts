import { test } from "node:test";
import assert from "node:assert/strict";
import { approvedPublicLink, disabledPublicIntegrations } from "./public.ts";

test("no integrations are enabled or initialized by default", () => {
  const state = disabledPublicIntegrations();
  assert.equal(state.status, "disabled");
  assert.equal(state.analyticsEnabled, false);
  assert.equal(state.bookingEnabled, false);
  assert.equal(state.feedbackEnabled, false);
  assert.equal(state.tickets, null);
  assert.deepEqual(state.social, []);
});

test("external link requires explicit customer editorial approval", () => {
  assert.equal(approvedPublicLink("tickets", "Купить", "https://tickets.example.org/events/1", false), null);
  const link = approvedPublicLink("tickets", "Билеты", "https://tickets.example.org/events/1", true);
  assert.equal(link?.target, "_blank");
  assert.equal(link?.rel, "noopener noreferrer");
  assert.equal(link?.kind, "tickets");
});

test("never pass secrets, private addresses or non-https targets", () => {
  for (const url of [
    "javascript:alert(1)", "data:text/html,hello",
    "http://tickets.example.org", "https://localhost/secret", "https://intranet.local/path",
    "https://user:pass@tickets.example.org/",
    "https://tickets.example.org/?api_key=x", "https://tickets.example.org/?auth_token=x",
    "mailto:person@example.org",
  ]) {
    assert.equal(approvedPublicLink("tickets", "Билеты", url, true), null, url);
  }
});

test("approved public media link needs no external SDK or user data", () => {
  const link = approvedPublicLink("video", "Видео", "https://example.org/watch/v/1", true);
  assert.equal(link?.href, "https://example.org/watch/v/1");
});
