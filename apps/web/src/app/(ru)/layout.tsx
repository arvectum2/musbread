import type { Metadata } from "next";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import "../globals.scss";
const siteApproved = process.env.MUSBREAD_SITE_APPROVED === "true";
export const metadata: Metadata = {
  title: { default: "Музей Хлеба — предконтрактный прототип", template: "%s | Музей Хлеба" },
  description: "Технический прототип информационного сайта музея. Неофициальная тестовая версия.",
  metadataBase: new URL("https://musbread.ru"),
  robots: { index: siteApproved, follow: siteApproved },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body><SiteHeader/><main id="main" tabIndex={-1}>{children}</main><SiteFooter/></body></html>;
}
