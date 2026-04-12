"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Console" },
  { href: "/calendar", label: "Calendar" },
];

export default function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="rounded-[28px] border border-white/10 bg-slate-950/65 px-5 py-4 shadow-[0_20px_80px_rgba(0,0,0,0.35)] backdrop-blur">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.32em] text-amber-300/80">
            AirPro HVAC
          </p>
          <div className="flex items-end gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-stone-50">
              Service Command
            </h1>
            <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[0.7rem] font-medium uppercase tracking-[0.24em] text-emerald-200">
              Live
            </span>
          </div>
        </div>

        <nav className="flex flex-wrap items-center gap-2">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-amber-300 text-slate-950 shadow-[0_10px_30px_rgba(245,158,11,0.28)]"
                    : "border border-white/10 bg-white/5 text-slate-200 hover:border-amber-300/35 hover:bg-white/10"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
