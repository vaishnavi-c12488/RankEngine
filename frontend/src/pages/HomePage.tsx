import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Brain, Clock, Layers, Search, Trash2, Zap } from "lucide-react";
import { SearchBar } from "../components/SearchBar";
import { POPULAR_CATEGORIES, EXAMPLE_QUERIES, DEFAULT_LOCALE } from "../lib/constants";
import { clearHistory, readHistory, type HistoryEntry } from "../lib/history";
import { searchUrl } from "../lib/urls";
import type { Locale } from "../types";

const STEPS = [
  {
    icon: Search,
    title: "1. Understand the query",
    text: "Your search is converted into a dense vector by a sentence-transformer bi-encoder (all-MiniLM-L6-v2).",
  },
  {
    icon: Layers,
    title: "2. Retrieve candidates",
    text: "Qdrant finds the nearest product vectors in the marketplace you selected.",
  },
  {
    icon: Brain,
    title: "3. Rerank with LambdaMART",
    text: "A LightGBM learning-to-rank model reorders the candidates using query–product features.",
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const { hash } = useLocation();
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [locale, setLocale] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    document.title = "RankEngine | AI-powered product search";
    setHistory(readHistory());
  }, []);

  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
    else window.scrollTo(0, 0);
  }, [hash]);

  const go = (q: string, l: Locale) => navigate(searchUrl(q, l));

  return (
    <>
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 pb-14 pt-12 text-center sm:px-6 sm:pt-16 lg:px-8">
          <p className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
            <Zap className="h-3.5 w-3.5" aria-hidden="true" /> AI-powered product search
          </p>
          <h1 className="text-balance text-3xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            Find the right product, ranked by relevance
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-slate-600 sm:text-lg">
            RankEngine combines semantic vector retrieval with a learned ranking model to surface the
            products that best match what you mean, not just the words you type.
          </p>

          <div className="mt-8 text-left">
            <SearchBar large autoFocus initialLocale={locale} onLocaleChange={setLocale} onSearch={go} />
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-2" aria-label="Example searches">
            <span className="text-sm text-slate-500">Try:</span>
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => go(q, locale)}
                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-16 px-4 py-14 sm:px-6 lg:px-8">
        {history.length > 0 && (
          <section aria-labelledby="recent-heading">
            <div className="mb-4 flex items-center justify-between">
              <h2 id="recent-heading" className="text-lg font-semibold text-slate-900">
                Recent searches
              </h2>
              <button
                type="button"
                onClick={() => {
                  clearHistory();
                  setHistory([]);
                }}
                className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" /> Clear
              </button>
            </div>
            <ul className="flex flex-wrap gap-2">
              {history.map((h) => (
                <li key={`${h.query}-${h.locale}`}>
                  <button
                    type="button"
                    onClick={() => go(h.query, h.locale)}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:border-indigo-300 hover:bg-indigo-50"
                  >
                    <Clock className="h-4 w-4 text-slate-400" aria-hidden="true" />
                    {h.query}
                    <span className="badge">{h.locale.toUpperCase()}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section aria-labelledby="popular-heading">
          <h2 id="popular-heading" className="mb-4 text-lg font-semibold text-slate-900">
            Popular search categories
          </h2>
          <p className="mb-4 text-sm text-slate-500">
            These are starting points for a search, not a product inventory.
          </p>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {POPULAR_CATEGORIES.map((c) => (
              <li key={c.label}>
                <button
                  type="button"
                  onClick={() => go(c.query, locale)}
                  className="card flex h-full w-full flex-col items-start gap-1 p-4 text-left transition-shadow hover:shadow-md"
                >
                  <span className="text-sm font-semibold text-slate-900">{c.label}</span>
                  <span className="text-xs text-slate-500">“{c.query}”</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section id="how-it-works" aria-labelledby="how-heading" className="scroll-mt-24">
          <h2 id="how-heading" className="mb-6 text-lg font-semibold text-slate-900">
            How RankEngine works
          </h2>
          <ol className="grid gap-5 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }) => (
              <li key={title} className="card p-5">
                <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="font-semibold text-slate-900">{title}</h3>
                <p className="mt-1.5 text-sm text-slate-600">{text}</p>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </>
  );
}
