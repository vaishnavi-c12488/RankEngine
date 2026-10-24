import { Search } from "lucide-react";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white" aria-hidden="true">
        <Search className="h-4 w-4" strokeWidth={2.75} />
      </span>
      <span className="text-lg font-bold tracking-tight text-slate-900">
        Rank<span className="text-indigo-600">Engine</span>
      </span>
    </span>
  );
}
