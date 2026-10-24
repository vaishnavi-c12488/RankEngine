import { Logo } from "./Logo";
import { useIndexInfo } from "../lib/useIndexInfo";

export function Footer() {
  const info = useIndexInfo();
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl space-y-3 px-4 py-8 text-sm text-slate-600 sm:px-6 lg:px-8">
        <Logo />
        <p className="max-w-3xl">
          RankEngine is a product-search and ranking demonstration: a sentence-transformer
          bi-encoder retrieves candidates from a Qdrant vector index and a LightGBM LambdaMART
          model reranks them. It is not a store: there is no cart, checkout or purchasing.
        </p>
        <p className="max-w-3xl text-slate-500">
          Product data comes from the Amazon Shopping Queries (ESCI) catalog.{" "}
          {info?.development_subset
            ? `This demo searches a development subset of ${info.product_count?.toLocaleString() ?? "a limited number of"} products, not the full catalog.`
            : "The index used by this demo may cover only a subset of the full catalog."}
        </p>
      </div>
    </footer>
  );
}
