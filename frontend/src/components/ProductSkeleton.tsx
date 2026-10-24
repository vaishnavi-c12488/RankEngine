export function ProductSkeleton() {
  return (
    <div className="card animate-pulse overflow-hidden" aria-hidden="true">
      <div className="h-40 bg-slate-100" />
      <div className="space-y-3 p-4">
        <div className="h-4 w-11/12 rounded bg-slate-200" />
        <div className="h-4 w-2/3 rounded bg-slate-200" />
        <div className="h-3 w-1/3 rounded bg-slate-100" />
        <div className="h-3 w-full rounded bg-slate-100" />
        <div className="h-3 w-5/6 rounded bg-slate-100" />
        <div className="h-9 w-full rounded-lg bg-slate-100" />
      </div>
    </div>
  );
}

export function ResultsSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div role="status" aria-busy="true" aria-label="Loading search results">
      <span className="sr-only">Searching products…</span>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: count }, (_, i) => (
          <ProductSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
