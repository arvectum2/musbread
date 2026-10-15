"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { MuseumEvent } from "@/data/types";

/** Keyboard-operable combobox; focus stays on input while arrows select. */
export default function EventSearch({ events }: { events: MuseumEvent[] }) {
  const router = useRouter();
  const listId = useId();
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    // SSR markup is visible before client search handlers have been attached.
    // Expose readiness for assistive/automated verification of interactivity.
    const ready = window.requestAnimationFrame(() => setHydrated(true));
    return () => window.cancelAnimationFrame(ready);
  }, []);
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const activeIndexRef = useRef(-1);
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("ru");
    if (needle.length < 2) return [];
    return events.filter((event) =>
      [event.title, event.category, event.excerpt].some((field) =>
        field.toLocaleLowerCase("ru").includes(needle),
      ),
    ).slice(0, 7);
  }, [events, query]);
  const isSearching = query.trim().length >= 2;
  const showOptions = expanded && isSearching && results.length > 0;
  const activeOptionId =
    showOptions && activeIndex >= 0 && activeIndex < results.length
      ? `${listId}-option-${activeIndex}`
      : undefined;

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
          activeIndexRef.current = -1;
          setActiveIndex(-1);
          setExpanded(true);
        }}
        onFocus={() => setExpanded(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            // Search inputs clear themselves on Escape in some engines unless
            // default behavior is prevented. Closing suggestions must not
            // silently discard the user's query.
            event.preventDefault();
            setExpanded(false);
            activeIndexRef.current = -1;
            setActiveIndex(-1);
            return;
          }
          if ((event.key === "ArrowDown" || event.key === "ArrowUp") && results.length) {
            event.preventDefault();
            setExpanded(true);
            const current = activeIndexRef.current;
            const next = event.key === "ArrowDown"
              ? (current + 1) % results.length
              : current <= 0 ? results.length - 1 : current - 1;
            activeIndexRef.current = next;
            setActiveIndex(next);
            return;
          }
          // Ref avoids losing an immediate ArrowDown + Enter before React repaints.
          if (event.key === "Enter" && results.length && activeIndexRef.current >= 0) {
            event.preventDefault();
            setExpanded(false);
            router.push("/events/" + results[activeIndexRef.current].slug + "/");
          }
        }}
        data-ready={hydrated ? "true" : "false"}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showOptions}
        aria-controls={listId}
        aria-activedescendant={activeOptionId}
        aria-describedby="search-hint"
      />
      <p id="search-hint" className="search-hint">
        Введите два символа; используйте стрелки для выбора, Enter для перехода, Esc для закрытия.
      </p>
      <div id={listId} role="listbox" aria-label="Результаты поиска по событиям"
        className="search-results" hidden={!showOptions}>
        {showOptions && results.map((result, index) => (
          <Link
            role="option"
            aria-selected={index === activeIndex}
            id={`${listId}-option-${index}`}
            href={`/events/${result.slug}/`}
            key={result.slug}
            className={index === activeIndex ? "active" : undefined}
            onMouseEnter={() => {
              activeIndexRef.current = index;
              setActiveIndex(index);
            }}
            onClick={() => {
              activeIndexRef.current = -1;
              setExpanded(false);
            }}
          >
            <strong>{result.title}</strong><span>{result.category}</span>
          </Link>
        ))}
      </div>
      {expanded && isSearching && results.length === 0 && (
        <p role="status" className="search-empty">По вашему запросу событий не найдено.</p>
      )}
    </div>
  );
}
