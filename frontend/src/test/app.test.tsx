import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import App from "../App";
import { _clearSearchCacheForTests } from "../pages/SearchPage";
import { _resetIndexInfoCacheForTests } from "../lib/useIndexInfo";

const RESULTS = {
  query: "headphones",
  locale: "us",
  candidates_retrieved: 50,
  results: [
    { rank: 1, product_id: "B000001", locale: "us", title: "Wireless Headphones Pro", description: "<p>Great <b>sound</b></p>", brand: "Acme", retrieval_score: 0.61, rerank_score: 1.5 },
    { rank: 2, product_id: "B000002", locale: "us", title: "Alpha Earbuds", description: "", brand: "", retrieval_score: 0.7, rerank_score: 0.9 },
  ],
};

const PRODUCTS: Record<string, unknown> = {
  "us/B000001": { product_id: "B000001", locale: "us", title: "Wireless Headphones Pro", description: "<p>Great <b>sound</b></p><p>Second paragraph &amp; more</p><script>alert(1)</script>", bullet_points: ["Bluetooth 5.0", "30 hour battery"], brand: "Acme", color: "Black" },
  "es/B000001": { product_id: "B000001", locale: "es", title: "Wireless Headphones Pro", description: "Sonido", bullet_points: [], brand: "Acme", color: "" },
  "us/B000002": { product_id: "B000002", locale: "us", title: "Alpha Earbuds", description: "", bullet_points: [], brand: "", color: "" },
};

type FetchCall = { url: string; init?: RequestInit };
let calls: FetchCall[] = [];

function mockBackend(opts: { searchStatus?: number; offline?: boolean; empty?: boolean } = {}) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      if (opts.offline) throw new TypeError("Failed to fetch");
      const json = (body: unknown, status = 200) =>
        new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/index-info")) return json({ product_count: 15000, locales: {}, development_subset: true, limit_per_locale: 5000, embedding_model: "m" });
      if (url.endsWith("/search")) {
        if (opts.searchStatus) return json({ detail: "boom" }, opts.searchStatus);
        if (opts.empty) return json({ ...RESULTS, candidates_retrieved: 0, results: [] });
        const body = JSON.parse(String(init?.body));
        return json({ ...RESULTS, locale: body.locale, results: RESULTS.results.map((r) => ({ ...r, locale: body.locale })) });
      }
      const m = url.match(/\/products\/([^?]+)\?locale=(\w+)/);
      if (m) {
        const hit = PRODUCTS[`${m[2]}/${decodeURIComponent(m[1])}`];
        return hit ? json(hit) : json({ detail: "not found" }, 404);
      }
      return json({}, 404);
    }),
  );
}

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );

beforeEach(() => {
  _clearSearchCacheForTests();
  _resetIndexInfoCacheForTests();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

describe("home page", () => {
  it("shows the search form, marketplaces and example searches", () => {
    mockBackend();
    renderAt("/");
    expect(screen.getByRole("combobox", { name: /search products/i })).toBeInTheDocument();
    const select = screen.getByRole("combobox", { name: /marketplace/i });
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual([
      expect.stringContaining("US"), expect.stringContaining("JP"), expect.stringContaining("ES"),
    ]);
    expect(screen.getByRole("button", { name: "Running shoes" })).toBeInTheDocument();
  });

  it("rejects an empty search without calling the API", async () => {
    mockBackend();
    renderAt("/");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/enter a product/i);
    expect(calls.some((c) => c.url.endsWith("/search"))).toBe(false);
  });

  it("clear button empties the input", async () => {
    mockBackend();
    renderAt("/");
    const input = screen.getByRole("combobox", { name: /search products/i });
    await userEvent.type(input, "shoes");
    await userEvent.click(screen.getByRole("button", { name: /clear search/i }));
    expect(input).toHaveValue("");
  });

  it("searches on Enter and sends the chosen marketplace", async () => {
    mockBackend();
    renderAt("/");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: /marketplace/i }), "jp");
    await userEvent.type(screen.getByRole("combobox", { name: /search products/i }), "headphones{Enter}");
    expect(await screen.findByRole("heading", { name: /results for “headphones”/i })).toBeInTheDocument();
    const search = calls.find((c) => c.url.endsWith("/search"))!;
    expect(JSON.parse(String(search.init?.body))).toMatchObject({ query: "headphones", locale: "jp" });
  });

  it("supports keyboard selection from suggestions", async () => {
    mockBackend();
    renderAt("/");
    const input = screen.getByRole("combobox", { name: /search products/i });
    await userEvent.click(input);
    await userEvent.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(calls.some((c) => c.url.endsWith("/search"))).toBe(true));
    expect(JSON.parse(String(calls.find((c) => c.url.endsWith("/search"))!.init?.body)).query).toBe("Wireless headphones");
  });
});

describe("search results", () => {
  it("renders real backend products as accessible cards", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=us");
    expect(await screen.findByRole("link", { name: /view details for wireless headphones pro/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/product/us/B000001"),
    );
    expect(screen.getByText(/2 products · ranked from 50 retrieved candidates/i)).toBeInTheDocument();
    expect(screen.getByText("Great sound")).toBeInTheDocument(); // HTML cleaned
    expect(screen.queryByText(/<p>/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/development subset of 15,000 products/i).length).toBeGreaterThan(0);
  });

  it("does not invent fields: missing brand/description are omitted", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=us");
    await screen.findByText("Alpha Earbuds");
    expect(screen.queryByText(/\$\d/)).not.toBeInTheDocument();
  });

  it("shows a loading skeleton while the request is pending", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=us");
    expect(screen.getByRole("status", { name: /loading search results/i })).toBeInTheDocument();
    await screen.findByText("Alpha Earbuds");
  });

  it("sorts by title and by retrieval score", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=us");
    await screen.findByText("Alpha Earbuds");
    const titles = () => screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titles()).toEqual(["Wireless Headphones Pro", "Alpha Earbuds"]);
    await userEvent.selectOptions(screen.getByLabelText(/sort by/i), "title");
    expect(titles()).toEqual(["Alpha Earbuds", "Wireless Headphones Pro"]);
    await userEvent.selectOptions(screen.getByLabelText(/sort by/i), "retrieval");
    expect(titles()).toEqual(["Alpha Earbuds", "Wireless Headphones Pro"]); // 0.70 > 0.61
  });

  it("shows an empty-results state", async () => {
    mockBackend({ empty: true });
    renderAt("/search?q=zzzz&locale=us");
    expect(await screen.findByText(/no products found for “zzzz”/i)).toBeInTheDocument();
  });

  it("shows a friendly error with retry when the backend is offline", async () => {
    mockBackend({ offline: true });
    renderAt("/search?q=headphones&locale=us");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/can't reach the rankengine service/i);
    expect(alert).not.toHaveTextContent(/TypeError|Failed to fetch/);
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("shows a friendly error on a 500 without leaking the detail", async () => {
    mockBackend({ searchStatus: 500 });
    renderAt("/search?q=headphones&locale=us");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/something went wrong on the server/i);
    expect(alert).not.toHaveTextContent("boom");
  });

  it("re-searches when the marketplace changes", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=us");
    await screen.findByText("Alpha Earbuds");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: /marketplace/i }), "es");
    await waitFor(() => {
      const bodies = calls.filter((c) => c.url.endsWith("/search")).map((c) => JSON.parse(String(c.init?.body)).locale);
      expect(bodies).toEqual(["us", "es"]);
    });
  });
});

describe("product details flow", () => {
  it("opens the product by ID + locale and shows full, clean details", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=us");
    await userEvent.click(await screen.findByRole("link", { name: /view details for wireless headphones pro/i }));

    expect(await screen.findByRole("heading", { level: 1, name: "Wireless Headphones Pro" })).toBeInTheDocument();
    expect(calls.some((c) => c.url.includes("/products/B000001?locale=us"))).toBe(true);
    expect(screen.getByText("Second paragraph & more")).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain("<script>alert");
    expect(screen.getByText("Great sound")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual(
      expect.arrayContaining(["Bluetooth 5.0", "30 hour battery"]),
    );
    expect(screen.getByText("Bluetooth 5.0")).toBeInTheDocument();
    expect(screen.getByText("30 hour battery")).toBeInTheDocument();
    expect(screen.getByText("Black", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText(/technical information/i)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /no product image/i })).toBeInTheDocument();
  });

  it("back link returns to the same search and marketplace", async () => {
    mockBackend();
    renderAt("/search?q=headphones&locale=es");
    await userEvent.click(await screen.findByRole("link", { name: /view details for wireless headphones pro/i }));
    await screen.findByRole("heading", { level: 1, name: "Wireless Headphones Pro" });
    const back = screen.getByRole("link", { name: /back to search results/i });
    expect(back).toHaveAttribute("href", expect.stringContaining("q=headphones"));
    expect(back).toHaveAttribute("href", expect.stringContaining("locale=es"));
    await userEvent.click(back);
    expect(await screen.findByRole("heading", { name: /results for “headphones”/i })).toBeInTheDocument();
  });

  it("labels missing fields instead of fabricating them", async () => {
    mockBackend();
    renderAt("/product/us/B000002");
    await screen.findByRole("heading", { level: 1, name: "Alpha Earbuds" });
    expect(screen.getByText(/no description is available/i)).toBeInTheDocument();
    expect(screen.getByText(/no bullet points are available/i)).toBeInTheDocument();
    expect(screen.getAllByText("Not available")).toHaveLength(2); // brand + color
    expect(screen.getByRole("link", { name: /back to home/i })).toBeInTheDocument();
  });

  it("shows a not-found state for an unknown product ID", async () => {
    mockBackend();
    renderAt("/product/us/NOPE");
    expect(await screen.findByRole("heading", { name: /product not found/i })).toBeInTheDocument();
  });

  it("treats an unknown marketplace as not found without calling the API", async () => {
    mockBackend();
    renderAt("/product/fr/B000001");
    expect(await screen.findByRole("heading", { name: /product not found/i })).toBeInTheDocument();
    expect(calls.some((c) => c.url.includes("/products/"))).toBe(false);
  });

  it("shows an error state when the backend is unreachable", async () => {
    mockBackend({ offline: true });
    renderAt("/product/us/B000001");
    expect(await screen.findByRole("alert")).toHaveTextContent(/can't reach the rankengine service/i);
  });

  it("copy button copies the product ID", async () => {
    mockBackend();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderAt("/product/us/B000001");
    await userEvent.click(await screen.findByRole("button", { name: /copy product id b000001/i }));
    expect(writeText).toHaveBeenCalledWith("B000001");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });
});

describe("navigation", () => {
  it("renders a 404 page for unknown routes", () => {
    mockBackend();
    renderAt("/nope");
    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();
  });

  it("mobile menu toggles and links work", async () => {
    mockBackend();
    renderAt("/search?q=x&locale=us");
    await userEvent.click(screen.getByRole("button", { name: /open menu/i }));
    const nav = screen.getByRole("navigation", { name: "Mobile" });
    await userEvent.click(within(nav).getByRole("link", { name: "Home" }));
    expect(await screen.findByRole("heading", { level: 1, name: /find the right product/i })).toBeInTheDocument();
  });
});
