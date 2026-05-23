import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PlusIcon } from "@/components/ui/icons";
import { QueueRow } from "@/components/review-queue/queue-row";
import { listExtractionsServer } from "@/lib/api-server";

// Always re-fetch on navigation — the queue changes any time an upload
// finishes. fetch's `no-store` already covers this client-side; here we
// force a fresh server render too.
export const dynamic = "force-dynamic";

/**
 * Review queue list. Server-component shell with a fetched-once table.
 * Step 4 lists ALL completed/failed extractions newest first; refined
 * filtering (low-confidence, needs-review) arrives with the Dashboard.
 */
export default async function ReviewQueuePage() {
  let items: Awaited<ReturnType<typeof listExtractionsServer>>["items"] = [];
  let total = 0;
  let loadError: string | null = null;

  try {
    const data = await listExtractionsServer({ page: 1, pageSize: 25 });
    items = data.items;
    total = data.total;
  } catch (err) {
    loadError = err instanceof Error ? err.message : String(err);
  }

  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      <div className="flex items-start justify-between gap-8 mb-7 flex-wrap">
        <div className="max-w-[720px] flex-1 min-w-0">
          <h1 className="font-serif text-[32px] tracking-[-0.02em] font-normal leading-tight m-0 mb-2.5">
            Review <em className="italic text-accent not-italic font-normal">queue</em>
          </h1>
          <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0">
            Every extraction you&apos;ve run, newest first. Click a row to open
            the side-by-side review.
          </p>
        </div>
        <Link href="/upload">
          <Button variant="primary">
            <PlusIcon size={14} strokeWidth={2} />
            New upload
          </Button>
        </Link>
      </div>

      {loadError ? (
        <div className="bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-xl p-5">
          <p className="font-serif text-[17px] font-medium m-0 mb-1">
            Couldn&apos;t load the queue
          </p>
          <p className="m-0 text-[13px] font-mono">{loadError}</p>
          <p className="m-0 mt-2 text-[12.5px]">
            Is the backend running on <code>localhost:8000</code>?
          </p>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-paper border border-line rounded-xl p-12 text-center">
          <p className="font-serif text-[20px] font-medium text-ink m-0 mb-2">
            No extractions yet
          </p>
          <p className="text-[13px] text-ink-3 m-0 mb-5">
            Head to Upload to extract your first document.
          </p>
          <Link href="/upload">
            <Button variant="accent">
              <PlusIcon size={14} strokeWidth={2} />
              Upload a document
            </Button>
          </Link>
        </div>
      ) : (
        <div className="bg-paper border border-line rounded-xl overflow-hidden">
          <div className="grid grid-cols-[32px_1fr_220px_140px_140px_auto] gap-3 items-center px-4 py-3 border-b border-line-2 bg-paper-2 font-mono text-[10.5px] text-ink-3 tracking-[0.06em] uppercase">
            <span />
            <span>Document</span>
            <span>Seller</span>
            <span>Type</span>
            <span>Grand total</span>
            <span>Status</span>
          </div>
          {items.map((item) => (
            <QueueRow key={item.extraction_id} item={item} />
          ))}
          {total > items.length && (
            <div className="px-4 py-3 border-t border-line-2 bg-paper-2 font-mono text-[11px] text-ink-3 tracking-[0.04em] text-center">
              Showing {items.length} of {total} · pagination lands later
            </div>
          )}
        </div>
      )}
    </main>
  );
}
