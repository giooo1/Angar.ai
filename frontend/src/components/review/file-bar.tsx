import Link from "next/link";

import { Chip } from "@/components/ui/chip";
import type { CanonicalInvoice } from "@/lib/canonical";
import type { ExtractionStatusResponse } from "@/lib/api-types";
import { ReextractButton } from "./reextract-button";

type Props = {
  extraction: ExtractionStatusResponse;
  canonical: CanonicalInvoice | null;
};

const DOCUMENT_TYPE_LABEL: Record<string, string> = {
  vat_invoice: "VAT invoice",
  regular_invoice: "Regular invoice",
  waybill: "Waybill",
  receipt: "Receipt",
  utility_bill: "Utility bill",
  payment_order: "Payment order",
  unknown: "Unknown",
};

/**
 * Top bar of the Review screen: back arrow → filename + sub-line →
 * status chips → re-extract button. Sits below the topbar.
 */
export function FileBar({ extraction, canonical }: Props) {
  const filename = canonical?.extraction.source_filename ?? "(unknown filename)";
  const docNumber = canonical?.document_number;
  const docDate = canonical?.document_date;
  const docType = canonical?.document_type ?? "unknown";
  const docTypeLabel = DOCUMENT_TYPE_LABEL[docType] ?? docType;
  const accepted = canonical?.accepted ?? true;
  const status = extraction.status;

  const subParts = [
    docNumber,
    docDate,
    `${(extraction.processing_time_ms ?? 0) / 1000}s extraction`,
  ].filter(Boolean);

  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3 bg-paper border border-line rounded-xl mb-4">
      <div className="flex items-center gap-3.5 min-w-0">
        <Link
          href="/review"
          aria-label="Back to review queue"
          className="p-1.5 rounded text-ink-3 hover:text-ink hover:bg-black/[0.04] transition-colors no-underline"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          >
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </Link>
        <span
          className="doc-thumb flex-shrink-0"
          style={{ width: 30, height: 38 }}
        />
        <div className="min-w-0">
          <div className="font-serif text-[17px] font-medium tracking-[-0.015em] text-ink overflow-hidden text-ellipsis whitespace-nowrap">
            {filename}
          </div>
          <div className="font-mono text-[11px] text-ink-3 tracking-[0.04em] mt-0.5">
            {subParts.length > 0 ? subParts.join(" · ") : extraction.extraction_id.slice(0, 8)}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {!accepted && <Chip variant="error">rejected</Chip>}
        <Chip variant={status === "completed" ? "green" : status === "failed" ? "error" : "warn"}>
          {docTypeLabel} · {status}
        </Chip>
        <ReextractButton documentId={extraction.document_id} />
      </div>
    </div>
  );
}
