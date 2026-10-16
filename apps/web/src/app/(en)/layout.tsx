import type { Metadata } from "next";
import EnglishHeader from "@/components/EnglishHeader";
import EnglishFooter from "@/components/EnglishFooter";
import "../globals.scss";

const siteApproved = process.env.MUSBREAD_SITE_APPROVED === "true";
export const metadata: Metadata = {
  title: { default: "Museum of Bread — English preview", template: "%s | Museum of Bread" },
  description: "English-language preview of the Museum of Bread.",
  metadataBase: new URL("https://musbread.ru"),
  robots: { index: siteApproved, follow: siteApproved },
};
export default function EnglishLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><EnglishHeader/><main id="main" tabIndex={-1}>{children}</main><EnglishFooter/></body></html>;
}
