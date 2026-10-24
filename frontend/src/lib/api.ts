import { API_URL } from "./config";
import { CANDIDATES_PER_SEARCH, RESULTS_PER_SEARCH } from "./constants";
import type { IndexInfo, Locale, ProductDetail, SearchResponse } from "../types";

export type ApiErrorKind = "network" | "timeout" | "not_found" | "validation" | "server";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

const TIMEOUT_MS = 60_000;

async function request<T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, TIMEOUT_MS);
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort);

  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal });
    if (!res.ok) {
      let detail = "";
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") detail = body.detail;
      } catch {
        /* non-JSON error body */
      }
      if (res.status === 404) throw new ApiError("not_found", detail || "Not found.", 404);
      if (res.status === 422) throw new ApiError("validation", detail || "Invalid request.", 422);
      throw new ApiError("server", "The search service returned an error.", res.status);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (signal?.aborted) throw err; // caller cancelled: let it handle the AbortError
    if (timedOut) throw new ApiError("timeout", "The request timed out.");
    throw new ApiError("network", "Cannot reach the RankEngine service.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

export function searchProducts(
  query: string,
  locale: Locale,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  return request<SearchResponse>(
    "/search",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        locale,
        top_k: RESULTS_PER_SEARCH,
        candidate_k: CANDIDATES_PER_SEARCH,
      }),
    },
    signal,
  );
}

export function getProduct(
  productId: string,
  locale: Locale,
  signal?: AbortSignal,
): Promise<ProductDetail> {
  return request<ProductDetail>(
    `/products/${encodeURIComponent(productId)}?locale=${encodeURIComponent(locale)}`,
    undefined,
    signal,
  );
}

export function getIndexInfo(signal?: AbortSignal): Promise<IndexInfo> {
  return request<IndexInfo>("/index-info", undefined, signal);
}

export function friendlyError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.kind) {
      case "network":
        return "We can't reach the RankEngine service. Make sure the backend is running and try again.";
      case "timeout":
        return "The search took too long to respond. Please try again.";
      case "validation":
        return err.message;
      case "not_found":
        return err.message;
      default:
        return "Something went wrong on the server. Please try again in a moment.";
    }
  }
  return "Something unexpected went wrong. Please try again.";
}
