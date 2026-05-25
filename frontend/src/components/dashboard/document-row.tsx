"use client";

import Link from "next/link";

import { Chip } from "@/components/ui/chip";
import { cn } from "@/lib/utils";
import type { ExtractionStatusResponse } from "@/lib/api-types";

type Props = {
  item: ExtractionStatusResponse;
  selected: boolean;
  onToggle: () => void;
};

/**
 * One row in the Documents archive: checkbox · thumb · filename/number · type ·
 * date · seller · grand total · status · Open. The row links to /review/<id>;
 * the checkbox toggles selection without navigating.
 */
export function DocumentRow({ item, selected, onToggle }: Props) {
  const canonical = item.canonical_data;
  const sellerName = canonical?.seller?.name ?? "—";
  const docNumber = canonical?.document_number ?? item.extraction_id.slice(0, 8);
  const docType = canonical?.document_type ?? "unknown";
  const docDate = canonical?.document_date ?? "—";
  const grandTotal = canonical?.grand_total;
  const isMkhedruli =
    canonical?.seller?.script === "mkhedruli" ||
    canonical?.seller?.script === "mixed";

  return (
    <Link
      href={`/review/${item.extraction_id}`}
      className={cn(
        "grid grid-cols-[44px_40px_1fr_120px_120px_200px_130px_110px_auto] gap-3 items-center px-4 py-3",
        "border-b border-line-2 last:border-b-0 transition-colors no-underline text-ink",
        selected ? "bg-accent-soft/40" : "hover:bg-paper-2",
      )}
    >
      {/* Full-cell hit area so a near-miss toggles instead of navigating. */}
      <label
        className="flex items-center justify-center h-full -my-3 py-3 cursor-pointer"
        aria-label="Select document"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onToggle();
        }}
      >
        <input
          type="checkbox"
          checked={selected}
          readOnly
          tabIndex={-1}
          className="w-4 h-4 pointer-events-none accent-[var(--color-accent-2)]"
        />
      </label>
      <span className="doc-thumb" style={{ width: 28, height: 36 }} />
      <div className="min-w-0">
        <div className="text-[13.5px] font-medium tracking-[-0.005em] overflow-hidden text-ellipsis whitespace-nowrap">
          {canonical?.extraction.source_filename ?? "(no filename)"}
        </div>
        <div className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em] mt-0.5">
          {docNumber}
        </div>
      </div>
      <div className="min-w-0">
        <Chip variant="default">{docType}</Chip>
      </div>
      <div className="font-mono text-[12px] text-ink-2 tracking-[0.02em]">
        {docDate}
      </div>
      <div
        className={
          isMkhedruli
            ? "font-serif italic text-ink text-[14px] overflow-hidden text-ellipsis whitespace-nowrap"
            : "text-[13px] text-ink-2 overflow-hidden text-ellipsis whitespace-nowrap"
        }
      >
        {sellerName}
      </div>
      <div className="font-mono text-[12.5px] text-ink-2">
        {grandTotal ? `${grandTotal.amount} ${grandTotal.currency}` : "—"}
      </div>
      <StatusChip status={item.status} />
      <span className="justify-self-end text-[13px] font-medium text-accent">Open</span>
    </Link>
  );
}

function StatusChip({ status }: { status: ExtractionStatusResponse["status"] }) {
  if (status === "completed") return <Chip variant="green">extracted</Chip>;
  if (status === "failed") return <Chip variant="error">failed</Chip>;
  return <Chip variant="warn">{status}</Chip>;
}
