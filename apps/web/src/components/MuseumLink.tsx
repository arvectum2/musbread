import NextLink from "next/link";
import type {ComponentProps} from "react";
import {museumLinkTitle} from "@/data/link-titles";

/** All internal Next navigation reuses one source-aware title policy. */
export default function MuseumLink(props:ComponentProps<typeof NextLink>){
  const href=typeof props.href==="string" ? props.href : props.href.pathname ?? "";
  // macOS WebKit can skip anchors in sequential focus by default. Explicit
  // tabindex=0 retains the normal DOM order and enables real Tab navigation
  // without installing a keyboard listener or changing OS preferences.
  return <NextLink {...props} tabIndex={props.tabIndex ?? 0}
    title={props.title || museumLinkTitle(href) || (href.startsWith("/") && !href.startsWith("//") ? "Открыть страницу музея" : undefined)}/>;
}
