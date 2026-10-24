import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";

export function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname, location.search, location.hash]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? "text-indigo-700" : "text-slate-600 hover:text-slate-900"
    }`;

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" aria-label="RankEngine home" className="rounded-md">
          <Logo />
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 sm:flex">
          <NavLink to="/" end className={linkClass}>
            Home
          </NavLink>
          <Link
            to={{ pathname: "/", hash: "#how-it-works" }}
            className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
          >
            How it works
          </Link>
        </nav>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-700 hover:bg-slate-100 sm:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-slate-200 bg-white px-4 py-2 sm:hidden">
          <ul className="flex flex-col">
            <li>
              <Link to="/" className="block rounded-md px-3 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50">
                Home
              </Link>
            </li>
            <li>
              <Link
                to={{ pathname: "/", hash: "#how-it-works" }}
                className="block rounded-md px-3 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50"
              >
                How it works
              </Link>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
