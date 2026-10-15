import Link from "next/link";

export default function NotFound() {
  return <html lang="ru">
    <head>
      <title>Страница не найдена | Музей Хлеба</title>
      <meta name="robots" content="noindex,nofollow"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
    </head>
    <body>
      <a href="#main" className="skip-link">К основному содержимому</a>
      <main id="main" style={{ maxWidth: "56rem", margin: "3rem auto", padding: "1rem", fontFamily: "system-ui" }}>
        <h1>Страница не найдена</h1>
        <p>Проверьте адрес или вернитесь на главную страницу музея.</p>
        <p><Link href="/">Перейти на главную</Link></p>
      </main>
    </body>
  </html>;
}
