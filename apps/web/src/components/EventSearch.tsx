"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { MuseumEvent } from "@/data/types";

export default function EventSearch({ events }: { events: MuseumEvent[] }) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("ru");
    if (needle.length < 2) return [];
    return events.filter((event) =>
      [event.title, event.category, event.excerpt].some((field) =>
        field.toLocaleLowerCase("ru").includes(needle),
      ),
    ).slice(0, 7);
  }, [events, query]);

  return (
    <div className="search-box">
      <label htmlFor="event-search">Поиск по событиям</label>
      <input
        id="event-search"
        type="search"
        placeholder="Например, экскурсия"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setExpanded(true);
        }}
        onFocus={() => setExpanded(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setExpanded(false);
        }}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded && query.trim().length >= 2}
        aria-controls="event-search-results"
        aria-describedby="search-hint"
      />
      <p id="search-hint" className="search-hint">Введите не менее двух символов.</p>
      <div id="event-search-results" role="listbox" className="search-results">
        {expanded && query.trim().length >= 2 && (
          results.length ? results.map((result) => (
            <Link
              role="option"
              aria-selected={false}
              href={`/events/${result.slug}/`}
              key={result.slug}
              onClick={() => setExpanded(false)}
            >
              <strong>{result.title}</strong><span>{result.category}</span>
            </Link>
          )) : <p className="search-empty">По вашему запросу событий не найдено.</p>
        )}
      </div>
    </div>
  );
}
