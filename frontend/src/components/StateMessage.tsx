import type { ReactNode } from "react";

export function StateMessage({
  icon,
  title,
  children,
  action,
  tone = "neutral",
}: {
  icon: ReactNode;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  tone?: "neutral" | "error";
}) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className="card mx-auto flex max-w-xl flex-col items-center px-6 py-12 text-center"
    >
      <div className={`mb-4 ${tone === "error" ? "text-rose-500" : "text-slate-400"}`} aria-hidden="true">
        {icon}
      </div>
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      {children && <div className="mt-2 text-sm text-slate-600">{children}</div>}
      {action && <div className="mt-6 flex flex-wrap justify-center gap-3">{action}</div>}
    </div>
  );
}
