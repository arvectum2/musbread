import type { Metadata } from "next";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "Музей Хлеба — предконтрактный прототип", template: "%s | Музей Хлеба" },
  description: "Технический прототип информационного сайта музея. Неофициальная тестовая версия.",
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body><SiteHeader/><main id="main">{children}</main><SiteFooter/></body></html>;
}
