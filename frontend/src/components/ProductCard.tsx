
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import type { Locale, RankingContext, SearchResult } from "../types";
import { localeLang } from "../lib/constants";
import { productUrl, type SortKey } from "../lib/urls";
import { htmlToText, shortDescription } from "../lib/text";
import { ImagePlaceholder } from "./ImagePlaceholder";

export function ProductCard({
  item,
  query,
  searchLocale,
  sort,
  brand,
}: {
  item: SearchResult;
  query: string;
  searchLocale: Locale;
  sort: SortKey;
  brand: string;
}) {
  // Remove HTML markup before displaying product descriptions.
  const cleanDescription = htmlToText(item.description ?? "");
  const description = shortDescription(cleanDescription);
  const lang = localeLang(item.locale);

  const ranking: RankingContext = {
    rank: item.rank,
    retrieval_score: item.retrieval_score,
    rerank_score: item.rerank_score,
  };

  const detailUrl = productUrl(item.product_id, item.locale, {
    query,
    locale: searchLocale,
    sort,
    brand: brand || undefined,
  });

  return (
    <article className="card group relative flex w-full flex-col overflow-hidden transition-shadow hover:shadow-md focus-within:ring-2 focus-within:ring-indigo-500">
      <ImagePlaceholder className="h-40" />

      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3
          lang={lang}
          className="line-clamp-3 text-sm font-semibold leading-snug text-slate-900"
        >
          <Link
            to={detailUrl}
            state={{ ranking }}
            className="after:absolute after:inset-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            aria-label={`View details for ${item.title || "untitled product"}`}
          >
            {item.title || "Untitled product"}
          </Link>
        </h3>

        {item.brand && (
          <p lang={lang} className="text-xs font-medium text-indigo-700">
            {item.brand}
          </p>
        )}

        {description && (
          <p
            lang={lang}
            className="line-clamp-3 text-sm leading-relaxed text-slate-600"
          >
            {description}
          </p>
        )}

        <div className="mt-auto space-y-3 pt-2">
          <p className="text-xs text-slate-500">
            ID{" "}
            <span className="font-mono text-slate-700">
              {item.product_id}
            </span>
          </p>

          <p className="rounded-md bg-slate-50 px-2 py-1.5 text-[11px] leading-4 text-slate-500">
            <span className="font-semibold text-slate-600">
              Rank #{item.rank}
            </span>
            {" · "}rerank {item.rerank_score.toFixed(3)}
            {" · "}retrieval {item.retrieval_score.toFixed(3)}
          </p>

          <Link
            to={detailUrl}
            state={{ ranking }}
            className="btn-secondary relative z-10 flex w-full items-center justify-center gap-2 group-hover:bg-indigo-50 group-hover:text-indigo-700"
          >
            View Details
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </article>
  );
}
