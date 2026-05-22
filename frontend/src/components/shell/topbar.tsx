"use client";

import { usePathname } from "next/navigation";
import { BellIcon, SearchIcon } from "@/components/ui/icons";

const CRUMB_LABELS: Record<string, string> = {
  "/upload": "Upload",
  "/dashboard": "Documents",
  "/review": "Review queue",
  "/settings": "Settings",
};

/**
 * Top bar: org crumb · current-screen crumb, search box, language
 * switcher, notifications bell, and avatar. Sticks to the top of the
 * viewport above the page scroll area.
 *
 * Org name + avatar are hardcoded until step 5 (auth) introduces a
 * real user/org. Search and lang switcher are visual stubs for step 3.
 */
export function Topbar() {
  const pathname = usePathname();
  // Match the start of the path so /dashboard/123 still resolves to "Documents".
  const matchKey = Object.keys(CRUMB_LABELS).find((k) => pathname.startsWith(k));
  const here = matchKey ? CRUMB_LABELS[matchKey] : "—";

  return (
    <header className="flex items-center justify-between gap-6 px-7 py-3.5 border-b border-line bg-bg sticky top-0 z-10">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2.5 font-mono text-[11px] text-ink-3 tracking-[0.04em] uppercase">
        <span>Mtkvari &amp; Co</span>
        <span className="text-ink-4">/</span>
        <span className="text-ink">{here}</span>
      </div>

      {/* Search */}
      <div className="flex-1 max-w-[480px] flex items-center gap-2 px-3 py-1.5 rounded-lg bg-paper border border-line text-[13px] text-ink-3">
        <SearchIcon size={14} />
        <input
          className="flex-1 border-0 outline-none bg-transparent text-[13.5px] text-ink placeholder:text-ink-3"
          placeholder="Search documents, vendors, amounts…"
          aria-label="Search"
        />
        <span className="font-mono text-[10px] text-ink-3 bg-bg px-1.5 py-0.5 rounded border border-line-2">
          ⌘K
        </span>
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-3.5">
        <span className="font-mono text-[11px] text-ink-3 tracking-[0.06em] cursor-pointer">
          <b className="text-ink font-medium">KA</b> · EN
        </span>
        <button
          type="button"
          aria-label="Notifications"
          className="p-1.5 rounded text-ink-2 hover:bg-black/[0.04] hover:text-ink transition-colors"
        >
          <BellIcon size={16} />
        </button>
        <span className="w-[30px] h-[30px] rounded-full bg-accent text-white grid place-items-center text-xs font-semibold tracking-[-0.01em]">
          M
        </span>
      </div>
    </header>
  );
}
