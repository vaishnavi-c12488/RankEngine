export type Locale = "us" | "jp" | "es";

export interface SearchResult {
  rank: number;
  product_id: string;
  locale: string;
  title: string;
  description: string;
  brand: string;
  retrieval_score: number;
  rerank_score: number;
}

export interface SearchResponse {
  query: string;
  locale: string;
  candidates_retrieved: number;
  results: SearchResult[];
}

export interface ProductDetail {
  product_id: string;
  locale: string;
  title: string;
  description: string;
  bullet_points: string[];
  brand: string;
  color: string;
}

export interface IndexInfo {
  product_count: number | null;
  locales: Record<string, number>;
  development_subset: boolean | null;
  limit_per_locale: number | null;
  embedding_model: string;
}

/** Ranking details handed from a result card to the product page. */
export interface RankingContext {
  rank: number;
  retrieval_score: number;
  rerank_score: number;
}
