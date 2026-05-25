import { redirect } from "next/navigation";

import { ArchiveFilters } from "@/components/dashboard/archive-filters";
import { DocumentsTable } from "@/components/dashboard/documents-table";
import { Pagination } from "@/components/dashboard/pagination";
import { listExtractionsServer } from "@/lib/api-server";
import { getServerSession } from "@/lib/auth";

const PAGE_SIZE = 25;

type SearchParams = Promise<{
  page?: string;
  q?: string;
  document_type?: string;
  accepted?: string;
  has_corrections?: string;
  date_from?: string;
  date_to?: string;
}>;

/**
 * Documents archive — server-rendered, paginated list of every extraction in
 * the org, with search + filter chips (state in the URL). Click a row to open
 * the side-by-side review.
 */
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const session = await getServerSession();
  if (!session) {
    redirect("/login");
  }

  const params = await searchParams;
  const requested = Number(params.page);
  const page =
    Number.isFinite(requested) && requested > 0 ? Math.floor(requested) : 1;

  const acceptedParam =
    params.accepted === "true" ? true : params.accepted === "false" ? false : undefined;
  const anyFilter = Boolean(
    params.q ||
      params.document_type ||
      params.accepted ||
      params.has_corrections ||
      params.date_from ||
      params.date_to,
  );

  // Querystring (minus page) for pagination links so filters survive paging.
  const baseParams = new URLSearchParams();
  for (const k of ["q", "document_type", "accepted", "has_corrections", "date_from", "date_to"] as const) {
    if (params[k]) baseParams.set(k, params[k] as string);
  }
  const baseQuery = baseParams.toString();

  let items: Awaited<ReturnType<typeof listExtractionsServer>>["items"] = [];
  let total = 0;
  let loadError: string | null = null;

  try {
    const data = await listExtractionsServer({
      page,
      pageSize: PAGE_SIZE,
      q: params.q,
      documentType: params.document_type,
      accepted: acceptedParam,
      hasCorrections: params.has_corrections === "true",
      dateFrom: params.date_from,
      dateTo: params.date_to,
    });
    items = data.items;
    total = data.total;
  } catch (err) {
    loadError = err instanceof Error ? err.message : String(err);
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const showingFrom = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const showingTo = Math.min(total, page * PAGE_SIZE);

  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      <h1 className="font-serif text-[32px] tracking-[-0.02em] font-normal leading-tight m-0 mb-2.5">
        Documents <em className="italic text-accent not-italic font-normal">library</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0 mb-6">
        {total === 0 && !anyFilter
          ? "Every document you extract will show up here, newest first."
          : `Showing ${showingFrom}–${showingTo} of ${total.toLocaleString()} · page ${page} of ${pageCount}.`}
      </p>

      {loadError ? (
        <div className="bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-xl p-5">
          <p className="font-serif text-[17px] font-medium m-0 mb-1">
            Couldn&apos;t load the library
          </p>
          <p className="m-0 text-[13px] font-mono">{loadError}</p>
          <p className="m-0 mt-2 text-[12.5px]">
            Is the backend running on <code>localhost:8000</code>?
          </p>
        </div>
      ) : (
        <>
          <ArchiveFilters />
          {total === 0 && anyFilter ? (
            <div className="bg-paper border border-line rounded-xl p-12 text-center text-[14px] text-ink-3">
              No documents match these filters.
            </div>
          ) : (
            <>
              <DocumentsTable items={items} />
              <Pagination page={page} pageCount={pageCount} query={baseQuery} />
            </>
          )}
        </>
      )}
    </main>
  );
}
