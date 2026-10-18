import type {AnchorHTMLAttributes} from "react";
import {museumLinkTitle} from "@/data/link-titles";

/** Native external, tel:, mailto:, and same-page anchors get equivalent
 * optional destination titles without changing default browser semantics. */
export default function MuseumAnchor(props:AnchorHTMLAttributes<HTMLAnchorElement>){
  // Native Safari/WebKit may exclude implicit links from Tab order.
  // tabindex=0 makes the original interactive anchor sequentially focusable
  // while preserving explicit author tabindex and all native link behaviour.
  return <a {...props} tabIndex={props.tabIndex ?? 0}
    title={props.title || museumLinkTitle(props.href ?? "")}/>;
}
