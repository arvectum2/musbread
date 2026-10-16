import { content } from "./content";
import { guidePages, menuGroups } from "./navigation";
import { museumReference } from "./museum-reference";
import { buildPublicSearchIndex, rankSearch, type SearchItem } from "./search-core";

/** The same immutable public snapshot used for page rendering, never private CMS. */
// The same factual snippets actually shown on these navigation pages.
const visitorFacts = [museumReference.address, museumReference.metro, museumReference.phone,
  museumReference.email, museumReference.openingHours, museumReference.admissionHours,
  museumReference.closedDay, museumReference.sanitaryDay].join(" ");
export const searchItems: readonly SearchItem[] = buildPublicSearchIndex(content, {
  menuGroups, guidePages,
  guideSearchText: {
    "/guide/museum-contacts/": visitorFacts,
    "/guide/plan-visit/": visitorFacts,
    "/guide/tickets-and-benefits/": visitorFacts,
    "/guide/accessible-museum/": "В музее имеются пандусы и подъёмник, экспозиции первого и второго этажей. " + museumReference.phone,
  },
});

export function museumSearch(query: string, limit = 8): SearchItem[] {
  return rankSearch(searchItems, query, limit);
}
