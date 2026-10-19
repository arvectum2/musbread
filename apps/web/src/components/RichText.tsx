import sanitizeHtml from "sanitize-html";
import {museumLinkTitle} from "@/data/link-titles";
import {localMuseumPhoto} from "@/data/museum-photo-assets";
import MuseumTableScrollKeys from "@/components/MuseumTableScrollKeys";

/**
 * Defense in depth: PHP sanitizes content before storage, and the static site
 * sanitizes again before converting HTML into build-time output.
 */
export default function RichText({ html }: { html: string }) {
  const safeHtml = sanitizeHtml(html, {
    allowedTags: [
      "p", "br", "strong", "em", "b", "i", "u",
      "ul", "ol", "li", "blockquote", "h2", "h3", "h4", "a",
      "table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td",
    ],
    allowedAttributes: {
      a: ["href", "title", "rel", "tabindex"],
      // The official site's original tariffs are wider than a 320px
      // viewport. Let keyboard-only and screen reader users focus + scroll
      // the actual table, without flattening real 2026 museum price cells.
      table: ["tabindex"],
      th: ["scope", "id", "colspan", "rowspan"],
      td: ["headers", "colspan", "rowspan"],
    },
    allowedSchemes: ["http", "https", "mailto"],
    allowedSchemesByTag: { a: ["http", "https", "mailto"] },
    transformTags: {
      table: () => ({
        tagName: "table",
        attribs: {tabindex: "0"},
      }),
      a: (_tag, attributes) => ({
        tagName: "a",
        attribs: {
          ...attributes,
          // Historical official-site anchors to JPEG/PNG are now permanent
          // local files after domain cutover, not retired Drupal paths.
          ...(attributes.href && localMuseumPhoto(attributes.href)
            ? {href:localMuseumPhoto(attributes.href)!} : {}),
          // Source HTML cannot force a hostile positive/negative tab order.
          // macOS WebKit also needs explicit 0 to focus article links via Tab.
          tabindex: attributes.href ? "0" : "-1",
          ...(attributes.title?.trim() || !attributes.href
            ? {} : {title: museumLinkTitle(attributes.href) ?? "Открыть ссылку из опубликованных материалов музея"}),
        },
      }),
    },
    disallowedTagsMode: "discard",
    enforceHtmlBoundary: true,
  });

  return <div className="article-content rich-text">
    <div dangerouslySetInnerHTML={{ __html: safeHtml }} />
    <MuseumTableScrollKeys />
  </div>;
}
