import { PackageSearch } from "lucide-react";

/** Neutral stand-in: the catalog supplies no product image URLs. */
export function ImagePlaceholder({ className = "", label = true }: { className?: string; label?: boolean }) {
  return (
    <div
      role="img"
      aria-label="No product image available"
      className={`flex flex-col items-center justify-center gap-2 bg-gradient-to-b from-slate-50 to-slate-100 text-slate-400 ${className}`}
    >
      <PackageSearch className="h-10 w-10" strokeWidth={1.5} aria-hidden="true" />
      {label && <span className="text-xs font-medium">No image available</span>}
    </div>
  );
}
