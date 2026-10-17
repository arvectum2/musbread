import NextLink from "next/link";
import type {ComponentProps} from "react";
import {museumLinkTitle} from "@/data/link-titles";

/** All internal Next navigation reuses one source-aware title policy. */
export default function MuseumLink(props:ComponentProps<typeof NextLink>){
  const href=typeof props.href==="string" ? props.href : props.href.pathname ?? "";
  return <NextLink {...props} title={props.title || museumLinkTitle(href)}/>;
}
