import source from "./official-exposition-rooms.json";

/** A documented public source edition, not a licensed museum photo library. */
export type OfficialExpositionRoom = {
  slug: string;
  title: string;
  source_url: string;
  captured_utc: string;
  excerpt: string;
  html: string;
  html_sha256: string;
  description_length: number;
  image_sources: { source_url: string; alt: string }[];
  media_rights_confirmed: false;
};

export const officialExpositionRooms = source.rooms as OfficialExpositionRoom[];
export const officialExpositionSource = source.listing_source_url;
export const officialExpositionCaptureDate = source.snapshot_utc.slice(0, 10);
export const officialExpositionSlugs = new Set(officialExpositionRooms.map(({ slug }) => slug));
