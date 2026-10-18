import type { Metadata } from "next";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import "../globals.scss";
export const metadata: Metadata = {
  title: { default: "Музей Хлеба — предконтрактный прототип", template: "%s | Музей Хлеба" },
  description: "Технический прототип информационного сайта музея. Неофициальная тестовая версия.",
  // A distinct museum hostname prevents Next's trailingSlash normalizer from
  // changing source-verified absolute canonical URLs into other URL paths.
  // This only resolves relative metadata; canonical stays muzei-xleb.ru.
  metadataBase: new URL("https://www.muzei-xleb.ru"),
  robots: { index: false, follow: false }, // Fail closed for all demo/CMS pages
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body><SiteHeader/><main id="main" tabIndex={-1}>{children}</main><SiteFooter/></body></html>;
}
