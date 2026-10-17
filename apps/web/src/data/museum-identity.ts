import { museumReference } from "./museum-reference";

/**
 * Pre-award: text is sourced from the official museum site, but no adopted
 * brand identity or artwork usage rights have been approved by the museum.
 * Add approved RU/EN assets here only after handover of signed masters.
 */
export const museumIdentity: Record<"ru" | "en", {
  name: string;
  approvedLogoSrc: string | null;
}> = {
  ru: { name: museumReference.shortName, approvedLogoSrc: null },
  en: { name: "Museum of Bread", approvedLogoSrc: null },
};
