import type { Locale } from "../types";

export const LOCALES: { value: Locale; label: string; short: string; lang: string }[] = [
  { value: "us", label: "United States", short: "US", lang: "en" },
  { value: "jp", label: "Japan", short: "JP", lang: "ja" },
  { value: "es", label: "Spain", short: "ES", lang: "es" },
];

export const DEFAULT_LOCALE: Locale = "us";

export function isLocale(value: string | null | undefined): value is Locale {
  return value === "us" || value === "jp" || value === "es";
}

export function localeLang(locale: string): string {
  return LOCALES.find((l) => l.value === locale)?.lang ?? "en";
}

export function localeLabel(locale: string): string {
  return LOCALES.find((l) => l.value === locale)?.label ?? locale.toUpperCase();
}

// Example searches only. They are prompts for the search box, not inventory.
export const EXAMPLE_QUERIES = [
  "Wireless headphones",
  "Laptop for programming",
  "Running shoes",
  "Smartphone with good camera",
  "Bluetooth speaker",
];

export const POPULAR_CATEGORIES: { label: string; query: string }[] = [
  { label: "Audio", query: "Wireless headphones" },
  { label: "Computers", query: "Laptop for programming" },
  { label: "Sports & Outdoors", query: "Running shoes" },
  { label: "Phones & Cameras", query: "Smartphone with good camera" },
  { label: "Speakers", query: "Bluetooth speaker" },
  { label: "Kitchen", query: "Stainless steel water bottle" },
];

export const RESULTS_PER_SEARCH = 24;
export const CANDIDATES_PER_SEARCH = 50;
