import type {AnchorHTMLAttributes} from "react";
import {museumLinkTitle} from "@/data/link-titles";

/** Native external, tel:, mailto:, and same-page anchors get equivalent
 * optional destination titles without changing default browser semantics. */
export default function MuseumAnchor(props:AnchorHTMLAttributes<HTMLAnchorElement>){
  return <a {...props} title={props.title || museumLinkTitle(props.href ?? "")}/>;
}
