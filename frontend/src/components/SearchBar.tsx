import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Clock, Search, X } from "lucide-react";
import type { Locale } from "../types";
import { DEFAULT_LOCALE, EXAMPLE_QUERIES, LOCALES, isLocale } from "../lib/constants";
import { readHistory, type HistoryEntry } from "../lib/history";

interface Suggestion {
  query: string;
  locale?: Locale;
  kind: "recent" | "example";
}

export function SearchBar({
  initialQuery = "",
  initialLocale = DEFAULT_LOCALE,
  onSearch,
  autoFocus = false,
  large = false,
  searchOnLocaleChange = false,
  onLocaleChange,
}: {
  initialQuery?: string;
  initialLocale?: Locale;
  onSearch: (query: string, locale: Locale) => void;
  autoFocus?: boolean;
  large?: boolean;
  searchOnLocaleChange?: boolean;
  onLocaleChange?: (locale: Locale) => void;
}) {
  const uid = useId();
  const listId = `${uid}-suggestions`;
  const errorId = `${uid}-error`;
  const [query, setQuery] = useState(initialQuery);
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Keep the box in sync when the URL (and so the props) change.
  useEffect(() => setQuery(initialQuery), [initialQuery]);
  useEffect(() => setLocale(initialLocale), [initialLocale]);
  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  const suggestions = useMemo<Suggestion[]>(() => {
    const needle = query.trim().toLowerCase();
    const matches = (s: string) => !needle || s.toLowerCase().includes(needle);
    const recent: Suggestion[] = history
      .filter((h) => matches(h.query))
      .map((h) => ({ query: h.query, locale: h.locale, kind: "recent" }));
    const seen = new Set(recent.map((r) => r.query.toLowerCase()));
    const examples: Suggestion[] = EXAMPLE_QUERIES.filter(
      (q) => matches(q) && !seen.has(q.toLowerCase()),
    ).map((q) => ({ query: q, kind: "example" }));
    return [...recent, ...examples].slice(0, 8);
  }, [query, history]);

  const showList = open && suggestions.length > 0;

  const submit = (q: string, l: Locale) => {
    const trimmed = q.trim();
    if (!trimmed) {
      setError("Enter a product to search for.");
      inputRef.current?.focus();
      return;
    }
    setError("");
    setOpen(false);
    setActive(-1);
    setQuery(trimmed);
    setLocale(l);
    onSearch(trimmed, l);
  };

  const choose = (s: Suggestion) => submit(s.query, s.locale && isLocale(s.locale) ? s.locale : locale);

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!showList) {
        setHistory(readHistory());
        setOpen(true);
        setActive(0);
      } else setActive((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp" && showList) {
      e.preventDefault();
      setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter" && showList && active >= 0) {
      e.preventDefault();
      choose(suggestions[active]);
    } else if (e.key === "Escape" && open) {
      e.preventDefault();
      setOpen(false);
      setActive(-1);
    }
  };

  const clear = () => {
    setQuery("");
    setError("");
    setActive(-1);
    inputRef.current?.focus();
  };

  const h = large ? "h-14" : "h-12";

  return (
    <form
      role="search"
      aria-label="Product search"
      onSubmit={(e) => {
        e.preventDefault();
        submit(query, locale);
      }}
      noValidate
    >
      <div
        ref={wrapRef}
        className="relative"
        onBlur={(e) => {
          if (!wrapRef.current?.contains(e.relatedTarget as Node)) {
            setOpen(false);
            setActive(-1);
          }
        }}
      >
        <div className={`flex w-full flex-col gap-2 sm:flex-row sm:gap-0 sm:rounded-xl sm:border sm:bg-white sm:shadow-sm ${error ? "sm:border-rose-400" : "sm:border-slate-300"}`}>
          <div className="relative sm:w-44 sm:shrink-0">
            <label htmlFor={`${uid}-locale`} className="sr-only">
              Marketplace
            </label>
            <select
              id={`${uid}-locale`}
              value={locale}
              onChange={(e) => {
                const next = e.target.value as Locale;
                setLocale(next);
                onLocaleChange?.(next);
                if (searchOnLocaleChange && query.trim()) submit(query, next);
              }}
              className={`${h} w-full rounded-xl border border-slate-300 bg-slate-50 px-3 text-sm font-medium text-slate-700 sm:rounded-r-none sm:rounded-l-xl sm:border-0 sm:border-r`}
            >
              {LOCALES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.short} · {l.label}
                </option>
              ))}
            </select>
          </div>

          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <label htmlFor={`${uid}-input`} className="sr-only">
              Search products
            </label>
            <input
              ref={inputRef}
              id={`${uid}-input`}
              type="text"
              role="combobox"
              aria-expanded={showList}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={showList && active >= 0 ? `${listId}-${active}` : undefined}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? errorId : undefined}
              autoComplete="off"
              maxLength={500}
              value={query}
              placeholder="Search for products, e.g. wireless headphones"
              onChange={(e) => {
                setQuery(e.target.value);
                setError("");
                setActive(-1);
                setHistory(readHistory());
                setOpen(true);
              }}
              onFocus={() => {
                setHistory(readHistory());
                setOpen(true);
              }}
              onKeyDown={onKeyDown}
              className={`${h} w-full rounded-xl border border-slate-300 bg-white pl-11 pr-11 text-base text-slate-900 placeholder:text-slate-400 sm:rounded-none sm:border-0`}
            />
            {query && (
              <button
                type="button"
                onClick={clear}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          <button type="submit" className={`btn-primary ${h} rounded-xl px-6 text-base sm:rounded-l-none sm:rounded-r-xl`}>
            Search
          </button>
        </div>

        {showList && (
          <ul
            id={listId}
            role="listbox"
            aria-label="Search suggestions"
            className="absolute left-0 right-0 z-20 mt-2 max-h-80 overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg sm:left-44"
          >
            {suggestions.map((s, i) => (
              <li
                key={`${s.kind}-${s.query}-${s.locale ?? ""}`}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => choose(s)}
                onMouseEnter={() => setActive(i)}
                className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm ${i === active ? "bg-indigo-50 text-indigo-900" : "text-slate-700"}`}
              >
                {s.kind === "recent" ? (
                  <Clock className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
                ) : (
                  <Search className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
                )}
                <span className="flex-1 truncate">{s.query}</span>
                <span className="text-xs text-slate-400">{s.kind === "recent" ? `Recent · ${s.locale?.toUpperCase()}` : "Example"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && (
        <p id={errorId} role="alert" className="mt-2 text-sm font-medium text-rose-600">
          {error}
        </p>
      )}
    </form>
  );
}
