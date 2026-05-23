"use client";

import { usePathname } from "next/navigation";

import { BellIcon, SearchIcon } from "@/components/ui/icons";
import { logout } from "@/lib/api";
import type { OrganizationDTO, UserDTO } from "@/lib/api-types";

const CRUMB_LABELS: Record<string, string> = {
  "/upload": "Upload",
  "/dashboard": "Documents",
  "/review": "Review queue",
  "/settings": "Settings",
};

type Props = {
  user: UserDTO;
  organization: OrganizationDTO;
};

/**
 * Top bar: org crumb · current-screen crumb, search box, language
 * switcher, notifications bell, avatar dropdown with logout.
 *
 * After step 5 the org / user data is the real authenticated session,
 * passed in from the (app) server-side layout. The avatar initial
 * comes from the user's full_name (or email when full_name is null).
 */
export function Topbar({ user, organization }: Props) {
  const pathname = usePathname();
  const matchKey = Object.keys(CRUMB_LABELS).find((k) => pathname.startsWith(k));
  const here = matchKey ? CRUMB_LABELS[matchKey] : "—";

  const initial = (user.full_name || user.email).trim().charAt(0).toUpperCase();

  return (
    <header className="flex items-center justify-between gap-6 px-7 py-3.5 border-b border-line bg-bg sticky top-0 z-10">
      <div className="flex items-center gap-2.5 font-mono text-[11px] text-ink-3 tracking-[0.04em] uppercase">
        <span>{organization.name}</span>
        <span className="text-ink-4">/</span>
        <span className="text-ink">{here}</span>
      </div>

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

      <div className="flex items-center gap-3.5">
        <span className="font-mono text-[11px] text-ink-3 tracking-[0.06em] cursor-pointer">
          <b className="text-ink font-medium">{user.locale === "ka" ? "KA" : "EN"}</b>
        </span>
        <button
          type="button"
          aria-label="Notifications"
          className="p-1.5 rounded text-ink-2 hover:bg-black/[0.04] hover:text-ink transition-colors"
        >
          <BellIcon size={16} />
        </button>
        <AvatarMenu initial={initial} email={user.email} />
      </div>
    </header>
  );
}

function AvatarMenu({ initial, email }: { initial: string; email: string }) {
  return (
    <div className="relative group">
      <button
        type="button"
        aria-label="Account menu"
        title={email}
        className="w-[30px] h-[30px] rounded-full bg-accent text-white grid place-items-center text-xs font-semibold tracking-[-0.01em] cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-bg"
      >
        {initial}
      </button>
      <div className="absolute top-full right-0 mt-2 min-w-[220px] bg-paper border border-line rounded-lg shadow-[0_20px_40px_-16px_rgba(20,15,5,0.18)] p-2 hidden group-hover:block group-focus-within:block">
        <div className="px-3 py-2 border-b border-line-2">
          <div className="font-mono text-[11px] text-ink-3 tracking-[0.04em] truncate">
            {email}
          </div>
        </div>
        <button
          type="button"
          onClick={async () => {
            try {
              await logout();
            } finally {
              window.location.href = "/login";
            }
          }}
          className="w-full text-left px-3 py-2 mt-1 rounded text-[13px] text-ink-2 hover:bg-paper-2 hover:text-ink cursor-pointer flex items-center gap-2"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            <path d="M16 17l5-5-5-5M21 12H9" />
          </svg>
          Sign out
        </button>
      </div>
    </div>
  );
}
