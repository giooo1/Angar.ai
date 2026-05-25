import Link from "next/link";

import { Chip } from "@/components/ui/chip";
import type { ExtractionStatusResponse } from "@/lib/api-types";

type Props = { item: ExtractionStatusResponse };

/**
 * One row in the Review queue list. Mirrors the App.html dashboard
 * table row but slimmer (no checkbox, no bulk actions yet).
 */
export function QueueRow({ item }: Props) {
  const canonical = item.canonical_data;
  const sellerName = canonical?.seller?.name ?? "—";
  const docNumber = canonical?.document_number ?? item.extraction_id.slice(0, 8);
  const grandTotal = canonical?.grand_total;
  const isMkhedruli =
    canonical?.seller?.script === "mkhedruli" ||
    canonical?.seller?.script === "mixed";

  return (
    <Link
      href={`/review/${item.extraction_id}`}
      className="grid grid-cols-[32px_1fr_200px_130px_110px_auto] gap-3 items-center px-4 py-3 border-b border-line-2 last:border-b-0 hover:bg-paper-2 transition-colors no-underline text-ink"
    >
      <span className="doc-thumb" style={{ width: 26, height: 32 }} />
      <div className="min-w-0">
        <div className="text-[13.5px] font-medium tracking-[-0.005em] overflow-hidden text-ellipsis whitespace-nowrap">
          {canonical?.extraction.source_filename ?? "(no filename)"}
        </div>
        <div className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em] mt-0.5">
          {docNumber}
        </div>
      </div>
      <div
        className={
          isMkhedruli
            ? "font-serif italic text-ink text-[14px]"
            : "text-[13px] text-ink-2"
        }
      >
        {sellerName}
      </div>
      <div className="font-mono text-[12.5px] text-ink-2">
        {grandTotal
          ? `${grandTotal.amount} ${grandTotal.currency}`
          : "—"}
      </div>
      <StatusChip status={item.status} />
      <span className="justify-self-end inline-flex items-center gap-1 text-[13px] font-medium text-accent">
        Review
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </span>
    </Link>
  );
}

function StatusChip({ status }: { status: ExtractionStatusResponse["status"] }) {
  if (status === "completed") return <Chip variant="green">extracted</Chip>;
  if (status === "failed") return <Chip variant="error">failed</Chip>;
  return <Chip variant="warn">{status}</Chip>;
}
