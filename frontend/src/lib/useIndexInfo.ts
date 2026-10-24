import { useEffect, useState } from "react";
import { getIndexInfo } from "./api";
import type { IndexInfo } from "../types";

let cached: IndexInfo | null = null;
let inflight: Promise<IndexInfo | null> | null = null;

function load(): Promise<IndexInfo | null> {
  if (cached) return Promise.resolve(cached);
  inflight ??= getIndexInfo()
    .then((info) => (cached = info))
    .catch(() => null)
    .finally(() => (inflight = null));
  return inflight;
}

/** Index metadata (size, development-subset flag). Null while unknown/unavailable. */
export function useIndexInfo(): IndexInfo | null {
  const [info, setInfo] = useState<IndexInfo | null>(cached);
  useEffect(() => {
    let live = true;
    load().then((v) => live && v && setInfo(v));
    return () => {
      live = false;
    };
  }, []);
  return info;
}

export function _resetIndexInfoCacheForTests() {
  cached = null;
  inflight = null;
}
