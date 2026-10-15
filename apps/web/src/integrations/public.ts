/**
 * Public/static integration boundaries. No provider SDKs, access tokens, cookies
 * or visitors' information may enter the public Next.js export.
 *
 * Links are customer-approved, manually supplied URLs only. This module
 * deliberately performs no HTTP request and injects no analytics script.
 */
export type PublicIntegrationKind = "tickets" | "maps" | "social" | "video";
export type IntegrationStatus = "disabled" | "ready";

export interface PublicIntegrationLink {
  readonly kind: PublicIntegrationKind;
  readonly label: string;
  readonly href: string;
  readonly rel: "noopener noreferrer";
  readonly target: "_blank";
}

const disallowedQueryKeys = /(^|[_-])(token|secret|key|pass(word)?|email|phone|session|auth)([_-]|$)/i;

/**
 * A client-facing link is not considered approved merely because it is a
 * syntactically valid HTTPS URL; explicit editorial approval is required.
 */
export function approvedPublicLink(
  kind: PublicIntegrationKind,
  label: string,
  candidate: string | null | undefined,
  approved: boolean,
): PublicIntegrationLink | null {
  if (!approved || !candidate || !label.trim() || label.length > 100) return null;
  try {
    const url = new URL(candidate);
    if (url.protocol !== "https:" || !url.hostname || url.username || url.password) return null;
    if (url.hostname === "localhost" || url.hostname.endsWith(".local")) return null;
    for (const key of url.searchParams.keys()) {
      if (disallowedQueryKeys.test(key)) return null;
    }
    return { kind, label: label.trim(), href: url.toString(), rel: "noopener noreferrer", target: "_blank" };
  } catch {
    return null;
  }
}

export interface StaticIntegrationState {
  readonly status: IntegrationStatus;
  readonly tickets: PublicIntegrationLink | null;
  readonly maps: PublicIntegrationLink | null;
  readonly social: readonly PublicIntegrationLink[];
  readonly video: readonly PublicIntegrationLink[];
  readonly analyticsEnabled: false;
  readonly feedbackEnabled: false;
  readonly bookingEnabled: false;
}

/** Safe default for all demo and production builds until the museum signs off. */
export function disabledPublicIntegrations(): StaticIntegrationState {
  return {
    status: "disabled",
    tickets: null,
    maps: null,
    social: [],
    video: [],
    analyticsEnabled: false,
    feedbackEnabled: false,
    bookingEnabled: false,
  };
}
