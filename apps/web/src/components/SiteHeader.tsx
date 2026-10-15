import Link from "next/link";
export default function SiteHeader() {
  return (
    <header className="site-header">
      <a href="#main" className="skip-link">Перейти к содержимому</a>
      <div className="header-inner">
        <Link href="/" className="wordmark" aria-label="Музей Хлеба — главная">
          <span className="brand-mark" aria-hidden="true">✳</span><span>МУЗЕЙ ХЛЕБА</span>
        </Link>
        <nav aria-label="Основное меню" className="main-nav">
          <Link href="/">Главная</Link>
          <Link href="/events/">Афиша</Link>
          <Link href="/museum/">Музей</Link>
          <Link href="/news/">Новости</Link>
          <a href="#contacts">Контакты</a>
        </nav>
        <details className="mobile-nav">
          <summary aria-label="Открыть меню">Меню ☰</summary>
          <nav aria-label="Мобильное меню"><Link href="/">Главная</Link><Link href="/events/">Афиша</Link><Link href="/museum/">Музей</Link><Link href="/news/">Новости</Link><Link href="/#contacts">Контакты</Link></nav>
        </details>
        <Link className="header-action" href="/events/">Посетить музей <span aria-hidden="true">↗</span></Link>
      </div>
    </header>
  );
}
