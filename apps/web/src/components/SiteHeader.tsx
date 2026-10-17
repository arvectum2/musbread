"use client";
import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import type { MouseEvent } from "react";
import GlobalSearch from "@/components/GlobalSearch";
import VisionMode from "@/components/VisionMode";
import { guideHref, museumReference } from "@/data/museum-reference";
import { menuGroups, navigationTree, usesCmsNavigation } from "@/data/navigation";
import NavigationBranch from "@/components/NavigationBranch";
import MuseumIdentity from "@/components/MuseumIdentity";

function closeAfterNavigation(event: MouseEvent<HTMLElement>) {
  if (!(event.target instanceof Element) || !event.target.closest("a")) return;
  event.currentTarget.querySelectorAll("details[open]").forEach((node) => {
    if (node instanceof HTMLDetailsElement) node.open = false;
  });
}
export default function SiteHeader() {
  return <header className="site-header">
    <MuseumAnchor href="#main" className="skip-link">Перейти к содержимому</MuseumAnchor>
    <div className="header-inner">
      <Link href="/" className="wordmark" aria-label="Санкт-Петербургский музей Хлеба — главная">
        <MuseumIdentity />
      </Link>
      <nav aria-label="Основное меню" className="main-nav" onClick={closeAfterNavigation}>
        {menuGroups.map((group) => <details className="mega-group" key={group.slug}>
          <summary>{group.title}</summary>
          <div className="mega-panel">
            <Link prefetch={false} href={"/guide/" + group.slug + "/"} className="mega-heading">Все подразделы: {group.title}</Link>
            {usesCmsNavigation
              ? <NavigationBranch nodes={navigationTree.find((node) => node.slug === group.slug)?.children ?? []} />
              : group.children.map((page) => <Link key={page.slug} prefetch={false} href={guideHref(page.slug)}>{page.title}</Link>)}
          </div>
        </details>)}
        <Link href="/news/">Новости</Link>
        <Link href="/guide/museum-contacts/">Контакты</Link>
      </nav>
      <div className="header-controls">
        <GlobalSearch compact />
        <VisionMode />
        <Link className="access-link" href="/guide/accessible-museum/" aria-label="Доступная среда: условия посещения">Доступная среда</Link>
        <MuseumAnchor className="header-action" href={museumReference.ticketUrl} target="_blank" rel="noopener noreferrer" aria-label="Купить билет на официальной площадке ВМузей (откроется новая вкладка)">Купить билет ↗</MuseumAnchor>
      </div>
      <details className="mobile-nav">
        <summary aria-label="Открыть меню">Меню ☰</summary>
        <nav aria-label="Мобильное меню" onClick={closeAfterNavigation}>
          <Link href="/">Главная</Link>
          <Link href="/search/">Поиск по сайту</Link>
          {menuGroups.map((group) => <details key={group.slug} className="mobile-subnav">
            <summary>{group.title}</summary>
            <div className="mobile-subnav-links">
              <Link prefetch={false} href={"/guide/" + group.slug + "/"}>Все подразделы</Link>
              {usesCmsNavigation
              ? <NavigationBranch nodes={navigationTree.find((node) => node.slug === group.slug)?.children ?? []} />
              : group.children.map((page) => <Link key={page.slug} prefetch={false} href={guideHref(page.slug)}>{page.title}</Link>)}
            </div>
          </details>)}
          <Link href="/news/">Новости</Link>
          <Link href="/guide/museum-contacts/">Контакты</Link>
          <Link href="/guide/accessible-museum/">Доступная среда</Link>
          <MuseumAnchor href={museumReference.ticketUrl} target="_blank" rel="noopener noreferrer">Купить билет ↗</MuseumAnchor>
        </nav>
      </details>
    </div>
  </header>;
}
