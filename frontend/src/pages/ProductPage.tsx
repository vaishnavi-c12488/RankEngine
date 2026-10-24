
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, PackageX } from "lucide-react";

import { CopyButton } from "../components/CopyButton";
import { ImagePlaceholder } from "../components/ImagePlaceholder";
import { StateMessage } from "../components/StateMessage";
import { ApiError, friendlyError, getProduct } from "../lib/api";
import { DEFAULT_LOCALE, isLocale, localeLabel, localeLang } from "../lib/constants";
import { htmlToText, toParagraphs } from "../lib/text";
import { searchUrl, type SortKey } from "../lib/urls";
import type { ProductDetail, RankingContext } from "../types";

type State =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "error"; message: string }
  | { status: "success"; product: ProductDetail };

const NA = <span className="text-slate-400">Not available</span>;

export default function ProductPage() {
  const { locale: rawLocale, productId = "" } = useParams();
  const [params] = useSearchParams();
  const location = useLocation();

  const ranking = (
    location.state as { ranking?: RankingContext } | null
  )?.ranking;

  const locale = isLocale(rawLocale) ? rawLocale : null;

  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  // Preserve the search context when navigating back.
  const fromQuery = (params.get("q") ?? "").trim();
  const sl = params.get("sl");
  const fromLocale = isLocale(sl) ? sl : locale ?? DEFAULT_LOCALE;

  const sortParam = params.get("sort");
  const fromSort: SortKey =
    sortParam === "title" || sortParam === "retrieval"
      ? sortParam
      : "relevance";

  const backTo = fromQuery
    ? searchUrl(
        fromQuery,
        fromLocale,
        fromSort,
        params.get("brand") ?? undefined,
      )
    : "/";

  const backLabel = fromQuery ? "Back to search results" : "Back to home";

  // Return nothing from this effect; scrolling needs no cleanup function.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [productId, rawLocale]);

  // Fetch product details and cancel requests when the page changes.
  useEffect(() => {
    if (!locale || !productId) {
      setState({ status: "not_found" });
      return;
    }

    const controller = new AbortController();
    let active = true;

    setState({ status: "loading" });

    getProduct(productId, locale, controller.signal)
      .then((product) => {
        if (active) {
          setState({ status: "success", product });
        }
      })
      .catch((err: unknown) => {
        if (!active || controller.signal.aborted) {
          return;
        }

        if (err instanceof ApiError && err.kind === "not_found") {
          setState({ status: "not_found" });
        } else if (
          err instanceof DOMException &&
          err.name === "AbortError"
        ) {
          return;
        } else {
          setState({
            status: "error",
            message: friendlyError(err),
          });
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [productId, locale, attempt]);

  // Update the browser tab title.
  useEffect(() => {
    if (state.status === "success") {
      document.title = `${state.product.title || "Product"} | RankEngine`;
    } else {
      document.title = "Product | RankEngine";
    }
  }, [state]);

  const back = (
    <Link
      to={backTo}
      className="inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-indigo-700 hover:text-indigo-900"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      {backLabel}
    </Link>
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">{back}</div>

      {state.status === "loading" && <ProductSkeleton />}

      {state.status === "not_found" && (
        <StateMessage
          icon={<PackageX className="h-10 w-10" />}
          title="Product not found"
          action={
            <Link to={backTo} className="btn-primary">
              {backLabel}
            </Link>
          }
        >
          We couldn’t find product{" "}
          <span className="font-mono">{productId}</span>
          {locale
            ? ` in the ${localeLabel(locale)} marketplace`
            : " (unknown marketplace)"}.
        </StateMessage>
      )}

      {state.status === "error" && (
        <StateMessage
          tone="error"
          icon={<AlertTriangle className="h-10 w-10" />}
          title="We couldn’t load this product"
          action={
            <>
              <button
                type="button"
                className="btn-primary"
                onClick={() => setAttempt((n) => n + 1)}
              >
                Try again
              </button>

              <Link to={backTo} className="btn-secondary">
                {backLabel}
              </Link>
            </>
          }
        >
          {state.message}
        </StateMessage>
      )}

      {state.status === "success" && (
        <Details
          product={state.product}
          ranking={ranking}
          fromQuery={fromQuery}
        />
      )}
    </div>
  );
}

function Details({
  product,
  ranking,
  fromQuery,
}: {
  product: ProductDetail;
  ranking?: RankingContext;
  fromQuery: string;
}) {
  const lang = localeLang(product.locale);

  const description = useMemo(
    () => toParagraphs(htmlToText(product.description ?? "")),
    [product.description],
  );

  const bullets = useMemo(
    () =>
      (product.bullet_points ?? [])
        .map((bullet) => htmlToText(bullet))
        .filter(Boolean),
    [product.bullet_points],
  );

  return (
    <article className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-12">
      <div>
        <div className="card overflow-hidden lg:sticky lg:top-24">
          <ImagePlaceholder className="aspect-square w-full" />
        </div>
      </div>

      <div className="space-y-8">
        <header className="space-y-3">
          {product.brand && (
            <p lang={lang} className="text-sm font-semibold text-indigo-700">
              {product.brand}
            </p>
          )}

          <h1
            lang={lang}
            className="text-2xl font-bold leading-snug tracking-tight text-slate-900 sm:text-3xl"
          >
            {product.title || "Untitled product"}
          </h1>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="badge">
              {localeLabel(product.locale)} ({product.locale.toUpperCase()})
            </span>

            {product.color && (
              <span className="badge">Color: {product.color}</span>
            )}

            <span className="flex items-center gap-2 text-sm text-slate-600">
              Product ID
              <span className="font-mono text-slate-900">
                {product.product_id}
              </span>
              <CopyButton
                value={product.product_id}
                label={`Copy product ID ${product.product_id}`}
              />
            </span>
          </div>
        </header>

        <section aria-labelledby="desc-heading">
          <h2
            id="desc-heading"
            className="mb-3 text-lg font-semibold text-slate-900"
          >
            Description
          </h2>

          {description.length > 0 ? (
            <div
              lang={lang}
              className="space-y-3 text-[15px] leading-relaxed text-slate-700"
            >
              {description.map((paragraph, index) => (
                <p key={index} className="whitespace-pre-line">
                  {paragraph}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No description is available for this product.
            </p>
          )}
        </section>

        <section aria-labelledby="bullets-heading">
          <h2
            id="bullets-heading"
            className="mb-3 text-lg font-semibold text-slate-900"
          >
            Product highlights
          </h2>

          {bullets.length > 0 ? (
            <ul
              lang={lang}
              className="list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-slate-700 marker:text-indigo-400"
            >
              {bullets.map((bullet, index) => (
                <li key={index}>{bullet}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              No bullet points are available for this product.
            </p>
          )}
        </section>

        <section aria-labelledby="meta-heading">
          <h2
            id="meta-heading"
            className="mb-3 text-lg font-semibold text-slate-900"
          >
            Product details
          </h2>

          <dl className="card divide-y divide-slate-100 text-sm">
            <Row
              label="Brand"
              value={
                product.brand ? (
                  <span lang={lang}>{product.brand}</span>
                ) : (
                  NA
                )
              }
            />

            <Row
              label="Color"
              value={
                product.color ? (
                  <span lang={lang}>{product.color}</span>
                ) : (
                  NA
                )
              }
            />

            <Row
              label="Product ID"
              value={<span className="font-mono">{product.product_id}</span>}
            />

            <Row
              label="Marketplace"
              value={`${localeLabel(product.locale)} (${product.locale.toUpperCase()})`}
            />

            <Row
              label="Price, rating, stock"
              value={
                <span className="text-slate-400">
                  Not available in this catalog
                </span>
              }
            />
          </dl>
        </section>

        {ranking && (
          <section aria-labelledby="tech-heading">
            <h2
              id="tech-heading"
              className="mb-3 text-lg font-semibold text-slate-900"
            >
              Technical information
            </h2>

            <dl className="card divide-y divide-slate-100 text-sm">
              <Row label="Search query" value={fromQuery || NA} />

              <Row
                label="Final rank (LambdaMART)"
                value={`#${ranking.rank}`}
              />

              <Row
                label="Rerank score"
                value={
                  <span className="font-mono">
                    {ranking.rerank_score.toFixed(4)}
                  </span>
                }
              />

              <Row
                label="Retrieval score (cosine)"
                value={
                  <span className="font-mono">
                    {ranking.retrieval_score.toFixed(4)}
                  </span>
                }
              />
            </dl>
          </section>
        )}
      </div>
    </article>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="grid grid-cols-3 gap-4 px-4 py-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="col-span-2 break-words text-slate-900">{value}</dd>
    </div>
  );
}

function ProductSkeleton() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading product"
      className="grid animate-pulse gap-8 lg:grid-cols-[5fr_7fr]"
    >
      <div className="aspect-square rounded-xl bg-slate-100" />

      <div className="space-y-4">
        <div className="h-4 w-24 rounded bg-slate-200" />
        <div className="h-8 w-3/4 rounded bg-slate-200" />
        <div className="h-4 w-1/2 rounded bg-slate-100" />
        <div className="h-32 w-full rounded bg-slate-100" />
        <div className="h-24 w-full rounded bg-slate-100" />
      </div>
    </div>
  );
}
