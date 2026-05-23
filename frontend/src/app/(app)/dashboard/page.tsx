import { redirect } from "next/navigation";

import { DocumentsTable } from "@/components/dashboard/documents-table";
import { Pagination } from "@/components/dashboard/pagination";
import { listExtractionsServer } from "@/lib/api-server";
import { getServerSession } from "@/lib/auth";

const PAGE_SIZE = 25;

type SearchParams = Promise<{ page?: string }>;

/**
 * Documents library — server-rendered, paginated list of every
 * extraction in the org. No search / filters in v1; those come when a
 * real customer asks. Click a row to land on the side-by-side review.
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

  let items: Awaited<ReturnType<typeof listExtractionsServer>>["items"] = [];
  let total = 0;
  let loadError: string | null = null;

  try {
    const data = await listExtractionsServer({ page, pageSize: PAGE_SIZE });
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
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0 mb-7">
        {total === 0
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
          <DocumentsTable items={items} />
          <Pagination page={page} pageCount={pageCount} />
        </>
      )}
    </main>
  );
}
