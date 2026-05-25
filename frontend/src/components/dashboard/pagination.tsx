import Link from "next/link";

type Props = {
  page: number;
  pageCount: number;
  /** Active filter querystring (without `page`) to preserve across paging. */
  query?: string;
};

/**
 * Minimal pagination: prev · current/total · next. Renders nothing for
 * single-page lists. Links carry the current filters + `?page=N` so the
 * server component re-runs with fresh, still-filtered data on navigation.
 */
export function Pagination({ page, pageCount, query }: Props) {
  if (pageCount <= 1) return null;

  const href = (p: number) => {
    const qs = new URLSearchParams(query ?? "");
    qs.set("page", String(p));
    return `/dashboard?${qs.toString()}`;
  };

  const prev = page > 1 ? page - 1 : null;
  const next = page < pageCount ? page + 1 : null;

  return (
    <nav
      aria-label="Pagination"
      className="mt-5 flex items-center justify-center gap-3 font-mono text-[12px] text-ink-3 tracking-[0.04em]"
    >
      <PageLink href={prev !== null ? href(prev) : null}>← Prev</PageLink>
      <span className="text-ink-2">
        Page <span className="text-ink font-medium">{page}</span> of {pageCount}
      </span>
      <PageLink href={next !== null ? href(next) : null}>Next →</PageLink>
    </nav>
  );
}

function PageLink({
  href,
  children,
}: {
  href: string | null;
  children: React.ReactNode;
}) {
  const base =
    "px-3 py-1.5 rounded border border-line bg-paper transition-colors";
  if (href === null) {
    return (
      <span className={`${base} opacity-40 cursor-not-allowed`}>{children}</span>
    );
  }
  return (
    <Link
      href={href}
      className={`${base} text-ink-2 hover:bg-paper-2 hover:text-ink no-underline`}
    >
      {children}
    </Link>
  );
}
