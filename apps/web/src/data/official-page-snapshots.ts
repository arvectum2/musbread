import source from "./official-page-snapshots.json";

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
export const officialSiteSnapshots = source.pages as OfficialPageSnapshot[];
export function officialSnapshotByPath(legacyPath?: string): OfficialPageSnapshot | undefined {
  if (!legacyPath) return undefined;
  return officialSiteSnapshots.find((page) => page.path === legacyPath);
}
