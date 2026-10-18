import type { Metadata } from "next";
import EnglishHeader from "@/components/EnglishHeader";
import EnglishFooter from "@/components/EnglishFooter";
import "../globals.scss";

export const metadata: Metadata = {
  title: { default: "Museum of Bread — English preview", template: "%s | Museum of Bread" },
  description: "English-language preview of the Museum of Bread.",
  // A distinct museum hostname prevents Next's trailingSlash normalizer from
  // changing source-verified absolute canonical URLs into other URL paths.
  // This only resolves relative metadata; canonical stays muzei-xleb.ru.
  metadataBase: new URL("https://www.muzei-xleb.ru"),
  robots: { index: false, follow: false }, // Fail closed for all demo/CMS pages
};
export default function EnglishLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><EnglishHeader/><main id="main" tabIndex={-1}>{children}</main><EnglishFooter/></body></html>;
}
