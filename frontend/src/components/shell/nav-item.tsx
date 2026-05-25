"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type Props = {
  href: string;
  icon: ReactNode;
  children: ReactNode;
  count?: number | string;
  /** Render the count as a red attention pill (and hide it when 0). */
  attention?: boolean;
};

/**
 * Sidebar nav item with active state derived from the URL pathname.
 * Active state matches when the current path starts with the item's href,
 * so /dashboard, /dashboard/123 both light up the Documents item.
 */
export function NavItem({ href, icon, children, count, attention }: Props) {
  const pathname = usePathname();
  const isActive =
    pathname === href || (href !== "/" && pathname.startsWith(href));

  const numericCount = typeof count === "number" ? count : Number(count);
  // Attention badges disappear at 0 (a clean queue shouldn't show a "0").
  const showCount =
    count !== undefined && (!attention || (Number.isFinite(numericCount) && numericCount > 0));

  return (
    <Link
      href={href}
      className={
        "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13.5px] " +
        "font-[450] tracking-[-0.005em] no-underline transition-colors " +
        (isActive
          ? "bg-white text-ink font-medium shadow-[0_1px_0_rgba(0,0,0,0.04),0_1px_2px_rgba(20,15,5,0.04)] [&_svg]:text-accent"
          : "text-ink-2 hover:bg-black/[0.035] hover:text-ink [&_svg]:text-ink-3")
      }
    >
      {icon}
      <span className="flex-1">{children}</span>
      {showCount &&
        (attention ? (
          <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1.5 rounded-full bg-error text-white font-mono text-[10px] font-semibold tracking-[0.02em]">
            {count}
          </span>
        ) : (
          <span className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em]">
            {count}
          </span>
        ))}
    </Link>
  );
}
