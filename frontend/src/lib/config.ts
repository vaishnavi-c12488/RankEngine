const raw = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

/** Backend base URL, configurable via VITE_API_URL. */
export const API_URL = raw.replace(/\/+$/, "");
