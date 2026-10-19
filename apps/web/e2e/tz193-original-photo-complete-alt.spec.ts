import { expect, test } from "@playwright/test";

/** TZ-193/194: short image alt does NOT erase archival museum captions. */
test("a museum ceramic exhibit has short alt and full original curator attribution on the link", async ({page}) => {
  await page.goto("/guide/exhibitions-virtual/");
  const image=page.locator('img[src="/media/museum-source/23855680df5ecfc32c31ec91e7a968db008569090ec57b9f0e70500c0b05bffd.webp"]');
  await expect(image).toHaveCount(1);
  const alt=await image.getAttribute("alt");
  expect(alt?.length).toBeLessThanOrEqual(125);
  expect(alt).toContain("супница");
  const anchor=image.locator("xpath=..");
  await expect(anchor).toHaveAccessibleName(/Товарищество производства фарфоровых/);
  await expect(anchor).toHaveAttribute("title", /Товарищество производства фарфоровых/);
});

test("an original museum historical opening-hours poster has concise alt and dated archival text", async ({page}) => {
  await page.goto("/news/museum-news-2025-12-30-grafik-raboty-muzeya/");
  const image=page.locator('img[src="/media/museum-source/1e8d70316948604221252e3fe5beed9f7a199dc385d2ceb4882dcb92a29175d1.webp"]');
  await expect(image).toHaveCount(1);
  const alt=await image.getAttribute("alt");
  expect(alt?.length).toBeLessThanOrEqual(125);
  expect(alt).toContain("января");
  await expect(image.locator("xpath=..")).toHaveAccessibleName(/Архивное объявление.*1, 2 января музей закрыт/);
});

test("legacy local archive index renders source photos with concise alts", async ({page}) => {
  await page.goto("/__museum_legacy_pager/page-6.html");
  const images=page.locator(".official-museum-program-card img");
  await expect(images).toHaveCount(2); // 10 articles, but only two genuine image links in this source page
  const alts=await images.evaluateAll(nodes=>nodes.map(n=>n.getAttribute("alt")||""));
  expect(alts.every(alt=>alt.length>0 && alt.length<=125)).toBe(true);
  expect(alts.some(alt=>alt.includes("музей закрыт"))).toBe(true);
});
