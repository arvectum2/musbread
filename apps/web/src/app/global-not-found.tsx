import Link from "@/components/MuseumLink";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import "./globals.scss";

export default function NotFound() {
  return <html lang="ru">
    <head>
      <title>Страница не найдена | Музей Хлеба</title>
      <meta name="robots" content="noindex,nofollow"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
    </head>
    <body>
      <SiteHeader />
      <main id="main" tabIndex={-1}>
        <section className="section inner-page">
          <nav className="breadcrumbs" aria-label="Хлебные крошки">
            <Link href="/">Главная</Link><span aria-hidden="true">/</span>
            <span aria-current="page">Страница не найдена</span>
          </nav>
          <h1>Страница не найдена</h1>
          <p>Проверьте адрес или вернитесь на главную страницу музея.</p>
          <p><Link href="/" className="text-link">Перейти на главную</Link></p>
        </section>
      </main>
      <SiteFooter />
    </body>
  </html>;
}
