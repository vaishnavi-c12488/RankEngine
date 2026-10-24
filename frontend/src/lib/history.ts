import type { Locale } from "../types";

export interface HistoryEntry {
  query: string;
  locale: Locale;
}

const KEY = "rankengine.history";
const MAX = 8;

export function readHistory(): HistoryEntry[] {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (e): e is HistoryEntry =>
        e && typeof e.query === "string" && (e.locale === "us" || e.locale === "jp" || e.locale === "es"),
    );
  } catch {
    return [];
  }
}

export function addToHistory(entry: HistoryEntry): HistoryEntry[] {
  const query = entry.query.trim();
  if (!query) return readHistory();
  const next = [
    { query, locale: entry.locale },
    ...readHistory().filter(
      (e) => !(e.query.toLowerCase() === query.toLowerCase() && e.locale === entry.locale),
    ),
  ].slice(0, MAX);
  try {
    sessionStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable: history is best-effort */
  }
  return next;
}

export function clearHistory(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
