import { addToHistory, clearHistory, readHistory } from "../lib/history";

describe("session search history", () => {
  it("adds most recent first and dedupes case-insensitively per locale", () => {
    addToHistory({ query: "shoes", locale: "us" });
    addToHistory({ query: "laptop", locale: "us" });
    addToHistory({ query: "Shoes", locale: "us" });
    expect(readHistory().map((h) => h.query)).toEqual(["Shoes", "laptop"]);
  });

  it("keeps the same query in different marketplaces", () => {
    addToHistory({ query: "shoes", locale: "us" });
    addToHistory({ query: "shoes", locale: "es" });
    expect(readHistory()).toHaveLength(2);
  });

  it("ignores blank queries, caps length, and clears", () => {
    addToHistory({ query: "  ", locale: "us" });
    expect(readHistory()).toEqual([]);
    for (let i = 0; i < 12; i++) addToHistory({ query: `q${i}`, locale: "us" });
    expect(readHistory()).toHaveLength(8);
    clearHistory();
    expect(readHistory()).toEqual([]);
  });

  it("tolerates corrupt storage", () => {
    sessionStorage.setItem("rankengine.history", "{not json");
    expect(readHistory()).toEqual([]);
  });
});
