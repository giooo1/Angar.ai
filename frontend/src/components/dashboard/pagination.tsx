import Link from "next/link";

type Props = {
  page: number;
  pageCount: number;
};

/**
 * Minimal pagination: prev · current/total · next. Renders nothing for
 * single-page lists. Links use `?page=N` so the server component re-runs
 * with fresh data on navigation.
 */
export function Pagination({ page, pageCount }: Props) {
  if (pageCount <= 1) return null;

  const prev = page > 1 ? page - 1 : null;
  const next = page < pageCount ? page + 1 : null;

  return (
    <nav
      aria-label="Pagination"
      className="mt-5 flex items-center justify-center gap-3 font-mono text-[12px] text-ink-3 tracking-[0.04em]"
    >
      <PageLink href={prev !== null ? `/dashboard?page=${prev}` : null}>
        ← Prev
      </PageLink>
      <span className="text-ink-2">
        Page <span className="text-ink font-medium">{page}</span> of {pageCount}
      </span>
      <PageLink href={next !== null ? `/dashboard?page=${next}` : null}>
        Next →
      </PageLink>
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
