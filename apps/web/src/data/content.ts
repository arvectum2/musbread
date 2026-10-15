import snapshot from "./published.json";
import type { MuseumSnapshot } from "./types";
export const content: MuseumSnapshot = snapshot;
export const events = content.events;
export const findEvent = (slug: string) => events.find((event) => event.slug === slug);
