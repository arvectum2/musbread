"use client";
import Link from "next/link";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { museumSearch } from "@/data/global-search-index";

export default function GlobalSearch({ compact = false, fullPage = false }: { compact?: boolean; fullPage?: boolean }) {
  const router = useRouter();
  const uid = useId();
  const listId = uid + "-list";
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const activeRef = useRef(-1);
  const [hydrated, setHydrated] = useState(false);
  const [showAll, setShowAll] = useState(false);
  useEffect(() => {
    // Static /search/ can be served with ?q=. Populate only after hydration.
    const initial = window.setTimeout(() => {
      if (fullPage) {
        const supplied = new URLSearchParams(window.location.search).get("q")?.slice(0, 180).trim() ?? "";
        if (supplied) { setQuery(supplied); setShowAll(true); }
      }
      setHydrated(true);
    }, 0);
    return () => window.clearTimeout(initial);
  }, [fullPage]);
  const results = useMemo(() => museumSearch(query), [query]);
  const allResults = useMemo(() => fullPage ? museumSearch(query, Number.MAX_SAFE_INTEGER) : [], [fullPage, query]);
  const visible = open && !showAll && query.trim().length > 1 && results.length > 0;
  const allPageUrl = query.trim()
    ? "/search/?q=" + encodeURIComponent(query.trim().slice(0, 180)) : "/search/";
  const navigateToAll = () => {
    if (fullPage) { setShowAll(true); setOpen(false); setActive(-1); activeRef.current = -1; }
    else router.push(allPageUrl);
  };
  const activeId = visible && active >= 0 && active < results.length ? listId + "-" + active : undefined;
  return <div className={compact ? "global-search compact" : "global-search"}>
    <label htmlFor={uid}>{compact ? "Поиск" : "Поиск по сайту"}</label>
    <input
      id={uid}
      type="search"
      autoComplete="off"
      value={query}
      placeholder="Поиск по музею"
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={visible}
      aria-controls={listId}
      aria-activedescendant={activeId}
      data-ready={hydrated ? "true" : "false"}
      onChange={(event) => { setQuery(event.target.value); setOpen(true); setActive(-1); activeRef.current = -1; setShowAll(false); }}
      onFocus={() => setOpen(true)}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault(); setOpen(false); setActive(-1); activeRef.current = -1;
          return;
        }
        if ((event.key === "ArrowDown" || event.key === "ArrowUp") && results.length) {
          event.preventDefault();
          setOpen(true);
          const current = activeRef.current;
          const next = event.key === "ArrowDown" ? (current + 1) % results.length
            : current <= 0 ? results.length - 1 : current - 1;
          activeRef.current = next; setActive(next);
          return;
        }
        if (event.key === "Enter" && query.trim().length > 1) {
          event.preventDefault();
          const selected = visible ? results[activeRef.current] : undefined;
          if (selected) {
            if (selected.download) window.location.assign(selected.href);
            else router.push(selected.href);
          } else navigateToAll();
        }
      }}
    />
    <div id={listId} role="listbox" className="global-search-options" aria-label="Результаты поиска по сайту" hidden={!visible}>
      {visible && results.map((item, index) => {
        const attributes = {
          role: "option" as const, "aria-selected": index === active,
          id: listId + "-" + index, className: index === active ? "active" : "",
          onMouseEnter: () => { activeRef.current = index; setActive(index); },
          onClick: () => { setOpen(false); setActive(-1); activeRef.current = -1; },
        };
        return item.download
          ? <a {...attributes} href={item.href} download key={item.href}><strong>{item.title}</strong><span>{item.section}</span></a>
          : <Link {...attributes} href={item.href} key={item.href}><strong>{item.title}</strong><span>{item.section}</span></Link>;
      })}
    </div>
    {open && query.trim().length > 1 && !results.length && <p role="status" className="global-search-empty">Материалы не найдены.</p>}
    <button type="button" className="global-search-submit" onClick={navigateToAll} aria-label={compact ? "Искать по всему сайту" : "Показать результаты поиска"}>
      {compact ? "Найти" : "Искать"}
    </button>
    {fullPage && query.trim().length > 1 && allResults.length > 0 && !showAll && <button type="button" className="search-all-button" onClick={() => { setShowAll(true); setOpen(false); setActive(-1); }}>Показать все результаты ({allResults.length})</button>}
    {fullPage && showAll && <section className="search-all-results" aria-label="Все результаты поиска">
      <p role="status">Найдено: {allResults.length}. Результаты сформированы по опубликованным материалам.</p>
      <ul>{allResults.map((item) => <li key={item.href}>
        {item.download ? <a href={item.href} download><strong>{item.title}</strong> · скачать</a>
          : <Link href={item.href}><strong>{item.title}</strong></Link>}
        <span className="search-result-section">{item.section}</span>
        {item.excerpt && <p>{item.excerpt}</p>}
      </li>)}</ul>
    </section>}
  </div>;
}
