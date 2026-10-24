import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle, Info, SearchX } from "lucide-react";
import { SearchBar } from "../components/SearchBar";
import { ProductCard } from "../components/ProductCard";
import { ResultsSkeleton } from "../components/ProductSkeleton";
import { StateMessage } from "../components/StateMessage";
import { ApiError, friendlyError, searchProducts } from "../lib/api";
import { DEFAULT_LOCALE, EXAMPLE_QUERIES, localeLabel, isLocale } from "../lib/constants";
import { addToHistory } from "../lib/history";
import { searchUrl, type SortKey } from "../lib/urls";
import { useIndexInfo } from "../lib/useIndexInfo";
import type { Locale, SearchResponse, SearchResult } from "../types";

// Responses are kept for the tab's lifetime so Back restores results instantly.
const cache = new Map<string, SearchResponse>();
export const _clearSearchCacheForTests = () => cache.clear();

const SORTS: { value: SortKey; label: string }[] = [
  { value: "relevance", label: "RankEngine relevance" },
  { value: "title", label: "Product title (A–Z)" },
  { value: "retrieval", label: "Retrieval score" },
];

function sortResults(items: SearchResult[], sort: SortKey): SearchResult[] {
  const copy = [...items];
  if (sort === "title") copy.sort((a, b) => (a.title || "").localeCompare(b.title || "", undefined, { sensitivity: "base" }));
  else if (sort === "retrieval") copy.sort((a, b) => b.retrieval_score - a.retrieval_score);
  else copy.sort((a, b) => a.rank - b.rank);
  return copy;
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: SearchResponse };

export default function SearchPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const info = useIndexInfo();

  const query = (params.get("q") ?? "").trim();
  const rawLocale = params.get("locale");
  const locale: Locale = isLocale(rawLocale) ? rawLocale : DEFAULT_LOCALE;
  const sortParam = params.get("sort");
  const sort: SortKey = sortParam === "title" || sortParam === "retrieval" ? sortParam : "relevance";
  const brand = params.get("brand") ?? "";

  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    document.title = query ? `${query} | RankEngine` : "Search | RankEngine";
  }, [query]);

  useEffect(() => {
    if (!query) return;
    const key = `${locale}|${query}`;
    const hit = cache.get(key);
    if (hit && attempt === 0) {
      setState({ status: "success", data: hit });
      addToHistory({ query, locale });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading" });
    searchProducts(query, locale, controller.signal)
      .then((data) => {
        cache.set(key, data);
        addToHistory({ query, locale });
        setState({ status: "success", data });
      })
      .catch((err) => {
        if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;
        setState({ status: "error", message: friendlyError(err) });
        if (err instanceof ApiError && err.kind === "validation") cache.delete(key);
      });
    return () => controller.abort();
  }, [query, locale, attempt]);

  // Restore scroll position when coming back to a results page.
  const scrollKey = `rankengine.scroll:${query}|${locale}`;
  useEffect(() => {
    if (state.status !== "success") return;
    const saved = Number(sessionStorage.getItem(scrollKey));
    if (saved > 0) window.scrollTo(0, saved);
    return () => {
      try {
        sessionStorage.setItem(scrollKey, String(window.scrollY));
      } catch {
        /* best effort */
      }
    };
  }, [state.status, scrollKey]);

  const onSearch = useCallback(
    (q: string, l: Locale) => {
      setAttempt(0);
      navigate(searchUrl(q, l));
    },
    [navigate],
  );

  const updateParams = (next: { sort?: SortKey; brand?: string }) =>
    navigate(searchUrl(query, locale, next.sort ?? sort, next.brand ?? brand), { replace: true });

  const data = state.status === "success" ? state.data : null;

  const brands = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.results.map((r) => r.brand).filter(Boolean))].sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: "base" }),
    );
  }, [data]);

  const visible = useMemo(() => {
    if (!data) return [];
    const filtered = brand ? data.results.filter((r) => r.brand === brand) : data.results;
    return sortResults(filtered, sort);
  }, [data, brand, sort]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <SearchBar initialQuery={query} initialLocale={locale} onSearch={onSearch} searchOnLocaleChange />
      </div>

      <div className="mt-8">
        {!query ? (
          <StateMessage icon={<SearchX className="h-10 w-10" />} title="Start with a search">
            <p>Type what you are looking for above, or try one of these examples.</p>
            <ExampleLinks locale={locale} />
          </StateMessage>
        ) : state.status === "loading" ? (
          <>
            <h1 className="page-title mb-6">
              Searching for “{query}”<span className="sr-only"> in {localeLabel(locale)}</span>
            </h1>
            <ResultsSkeleton />
          </>
        ) : state.status === "error" ? (
          <StateMessage
            tone="error"
            icon={<AlertTriangle className="h-10 w-10" />}
            title="We couldn’t complete your search"
            action={
              <button type="button" className="btn-primary" onClick={() => setAttempt((n) => n + 1)}>
                Try again
              </button>
            }
          >
            {state.message}
          </StateMessage>
        ) : data && data.results.length === 0 ? (
          <StateMessage icon={<SearchX className="h-10 w-10" />} title={`No products found for “${query}”`}>
            <p>No products were returned from the {localeLabel(locale)} marketplace. Try different words, or an example:</p>
            <ExampleLinks locale={locale} />
          </StateMessage>
        ) : data ? (
          <>
            <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h1 className="page-title">Results for “{data.query}”</h1>
                <p className="mt-1 text-sm text-slate-600" aria-live="polite">
                  {visible.length} {visible.length === 1 ? "product" : "products"}
                  {brand ? ` from ${brand}` : ""} · ranked from {data.candidates_retrieved} retrieved candidates ·{" "}
                  {localeLabel(data.locale)} marketplace
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {brands.length > 1 && (
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    Brand
                    <select
                      className="input max-w-[12rem]"
                      value={brand}
                      onChange={(e) => updateParams({ brand: e.target.value })}
                    >
                      <option value="">All brands</option>
                      {brands.map((b) => (
                        <option key={b} value={b}>
                          {b}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  Sort by
                  <select
                    className="input"
                    value={sort}
                    onChange={(e) => updateParams({ sort: e.target.value as SortKey })}
                  >
                    {SORTS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            {info?.development_subset && (
              <p className="mb-5 flex items-start gap-2 rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
                <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>
                  This demo searches a development subset of{" "}
                  {info.product_count ? `${info.product_count.toLocaleString()} products` : "the catalog"}, not the
                  full catalog, so some relevant products may not appear.
                </span>
              </p>
            )}

            {visible.length === 0 ? (
              <StateMessage icon={<SearchX className="h-10 w-10" />} title="No products match this filter">
                <button type="button" className="btn-secondary mt-2" onClick={() => updateParams({ brand: "" })}>
                  Show all brands
                </button>
              </StateMessage>
            ) : (
              <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {visible.map((item) => (
                  <li key={`${item.locale}:${item.product_id}`} className="flex">
                    <div className="flex w-full">
                      <ProductCard item={item} query={query} searchLocale={locale} sort={sort} brand={brand} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}

function ExampleLinks({ locale }: { locale: Locale }) {
  return (
    <ul className="mt-4 flex flex-wrap justify-center gap-2">
      {EXAMPLE_QUERIES.map((q) => (
        <li key={q}>
          <Link
            to={searchUrl(q, locale)}
            className="inline-block rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:border-indigo-300 hover:bg-indigo-50"
          >
            {q}
          </Link>
        </li>
      ))}
    </ul>
  );
}
