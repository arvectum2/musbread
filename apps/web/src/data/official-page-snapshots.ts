import source from "./official-page-snapshots.json";
import originalMenuGaps from "./official-museum-menu-gaps.json";

/** Captured on the Mac mini from the official domain; never live-fetched by Next. */
export type OfficialPageSnapshot = {
  path: string;
  source_url: string;
  title: string;
  captured_utc: string;
  html: string;
  text_sha256: string;
  html_sha256: string;
  text_length: number;
  document_links: readonly {url: string; label: string}[];
  image_links: readonly {url: string; alt: string}[];
};
// Additional literal existing museum menu pages not in the first
// page snapshot. Do NOT import guest-book visitor messages as institutional
// statements; COVID-19 rules from 2021 are historical and never presented
// as current visitor requirements.
const institutionPages = new Set([
  "/uchetnaya-politika",
  "/protivodeystvie-terrorizmu",
  "/antimonopolnyy-komplaens",
  "/adres",
]);
export const officialSiteSnapshots: OfficialPageSnapshot[] = [
  ...(source.pages as OfficialPageSnapshot[]),
  ...(originalMenuGaps.pages as OfficialPageSnapshot[])
    .filter((page) => institutionPages.has(page.path)),
];
export function officialSnapshotByPath(legacyPath?: string): OfficialPageSnapshot | undefined {
  if (!legacyPath) return undefined;
  return officialSiteSnapshots.find((page) => page.path === legacyPath);
}
