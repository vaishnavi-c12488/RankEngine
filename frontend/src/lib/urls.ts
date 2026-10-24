import type { Locale } from "../types";

export type SortKey = "relevance" | "title" | "retrieval";

export function searchUrl(query: string, locale: Locale, sort?: SortKey, brand?: string): string {
  const p = new URLSearchParams({ q: query, locale });
  if (sort && sort !== "relevance") p.set("sort", sort);
  if (brand) p.set("brand", brand);
  return `/search?${p.toString()}`;
}

/** Product URL that carries the originating search so "Back" can restore it. */
export function productUrl(
  productId: string,
  locale: string,
  from?: { query: string; locale: Locale; sort?: SortKey; brand?: string },
): string {
  const base = `/product/${encodeURIComponent(locale)}/${encodeURIComponent(productId)}`;
  if (!from) return base;
  const p = new URLSearchParams({ q: from.query, sl: from.locale });
  if (from.sort && from.sort !== "relevance") p.set("sort", from.sort);
  if (from.brand) p.set("brand", from.brand);
  return `${base}?${p.toString()}`;
}
