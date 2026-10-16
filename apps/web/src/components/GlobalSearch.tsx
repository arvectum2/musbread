"use client";
import Link from "next/link";
import { useId, useMemo, useState } from "react";
import { museumSearch } from "@/data/global-search-index";

export default function GlobalSearch({ compact = false, fullPage = false }: { compact?: boolean; fullPage?: boolean }) {
  const uid = useId();
  const listId = uid + "-list";
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [showAll, setShowAll] = useState(false);
  const results = useMemo(() => museumSearch(query), [query]);
  const allResults = useMemo(() => fullPage ? museumSearch(query, Number.MAX_SAFE_INTEGER) : [], [fullPage, query]);
  const visible = open && !showAll && query.trim().length > 1 && results.length > 0;
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
      onChange={(event) => { setQuery(event.target.value); setOpen(true); setActive(-1); setShowAll(false); }}
      onFocus={() => setOpen(true)}
      onKeyDown={(event) => {
        if (event.key === "Escape") { event.preventDefault(); setOpen(false); setActive(-1); }
        if ((event.key === "ArrowDown" || event.key === "ArrowUp") && results.length) {
          event.preventDefault();
          setOpen(true);
          setActive((a) => event.key === "ArrowDown" ? (a + 1) % results.length : a <= 0 ? results.length - 1 : a - 1);
        }
        if (event.key === "Enter" && active >= 0 && visible) {
          const selected = results[active];
          if (selected) window.location.assign(selected.href);
        }
      }}
    />
    <div id={listId} role="listbox" className="global-search-options" aria-label="Результаты поиска по сайту" hidden={!visible}>
      {visible && results.map((item, index) => <Link
        href={item.href}
        role="option"
        aria-selected={index === active}
        id={listId + "-" + index}
        className={index === active ? "active" : ""}
        key={item.href}
        onClick={() => { setOpen(false); setActive(-1); }}
      ><strong>{item.title}</strong><span>{item.section}</span></Link>)}
    </div>
    {open && query.trim().length > 1 && !results.length && <p role="status" className="global-search-empty">Материалы не найдены.</p>}
    {fullPage && query.trim().length > 1 && allResults.length > 0 && !showAll && <button type="button" className="search-all-button" onClick={() => { setShowAll(true); setOpen(false); setActive(-1); }}>Показать все результаты ({allResults.length})</button>}
    {fullPage && showAll && <section className="search-all-results" aria-label="Все результаты поиска">
      <p role="status">Найдено: {allResults.length}. Результаты сформированы по опубликованным материалам.</p>
      <ul>{allResults.map((item) => <li key={item.href}>
        <Link href={item.href}><strong>{item.title}</strong></Link>
        <span className="search-result-section">{item.section}</span>
        {item.excerpt && <p>{item.excerpt}</p>}
      </li>)}</ul>
    </section>}
  </div>;
}
