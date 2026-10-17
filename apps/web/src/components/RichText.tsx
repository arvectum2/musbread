import sanitizeHtml from "sanitize-html";
import {museumLinkTitle} from "@/data/link-titles";

/**
 * Defense in depth: PHP sanitizes content before storage, and the static site
 * sanitizes again before converting HTML into build-time output.
 */
export default function RichText({ html }: { html: string }) {
  const safeHtml = sanitizeHtml(html, {
    allowedTags: [
      "p", "br", "strong", "em", "b", "i", "u",
      "ul", "ol", "li", "blockquote", "h2", "h3", "h4", "a",
    ],
    allowedAttributes: { a: ["href", "title", "rel"] },
    allowedSchemes: ["http", "https", "mailto"],
    allowedSchemesByTag: { a: ["http", "https", "mailto"] },
    transformTags: {
      a: (_tag, attributes) => ({
        tagName: "a",
        attribs: {
          ...attributes,
          ...(attributes.title?.trim() || !attributes.href
            ? {} : {title: museumLinkTitle(attributes.href) ?? ""}),
        },
      }),
    },
    disallowedTagsMode: "discard",
    enforceHtmlBoundary: true,
  });

  return <div className="article-content rich-text" dangerouslySetInnerHTML={{ __html: safeHtml }} />;
}
