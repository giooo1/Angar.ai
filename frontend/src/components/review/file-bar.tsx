"use client";

import Link from "next/link";
import { useState } from "react";

import { Chip } from "@/components/ui/chip";
import { summarizeFieldStates } from "@/lib/confidence";
import type { CanonicalInvoice } from "@/lib/canonical";
import type { ExtractionStatusResponse } from "@/lib/api-types";
import { ExtractionSummary } from "./extraction-summary";

type Props = {
  extraction: ExtractionStatusResponse;
  canonical: CanonicalInvoice | null;
};

const DOC_TYPE_LABELS: Record<string, string> = {
  vat_invoice: "VAT invoice",
  regular_invoice: "Invoice",
  waybill: "Waybill",
  receipt: "Receipt",
  utility_bill: "Utility bill",
  payment_order: "Payment order",
  unknown: "Unknown",
};

/**
 * Top bar for the review screen: back arrow + thumb + filename + subtitle on
 * the left; a document-type/acceptance chip and a History toggle on the right.
 * History expands the extraction status summary (confidence banner + counts).
 */
export function FileBar({ extraction, canonical }: Props) {
  const [open, setOpen] = useState(false);

  // The model can't read the uploaded file's name (it emits a "<pdf filename>"
  // sentinel), so prefer the real filename the backend recorded on upload.
  const filename =
    extraction.original_filename ??
    canonical?.extraction.source_filename ??
    "(unknown filename)";
  const ms = extraction.processing_time_ms ?? 0;
  const sec = ms > 0 ? (ms / 1000).toFixed(1) : null;
  const sub = [sec ? `extracted ${sec}s` : null, "1 page"].filter(Boolean).join(" · ");

  const accepted = canonical?.accepted ?? true;
  const typeLabel = canonical
    ? DOC_TYPE_LABELS[canonical.document_type] ?? canonical.document_type
    : null;

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between gap-4 px-4 py-3 bg-paper border border-line rounded-xl">
        <div className="flex items-center gap-3.5 min-w-0">
          <Link
            href="/dashboard"
            aria-label="Back to documents"
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
          <span className="doc-thumb flex-shrink-0" style={{ width: 30, height: 38 }} />
          <div className="min-w-0">
            <div className="font-serif text-[16.5px] font-medium tracking-[-0.015em] text-ink overflow-hidden text-ellipsis whitespace-nowrap leading-tight">
              {filename}
            </div>
            <div className="font-mono text-[11px] text-ink-3 tracking-[0.04em] mt-0.5">
              {sub}
            </div>
          </div>
        </div>

        {canonical && (
          <div className="flex items-center gap-3 flex-none">
            <Chip variant={accepted ? "green" : "error"}>
              {typeLabel} · {accepted ? "accepted" : "rejected"}
            </Chip>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-3 hover:text-ink-2 font-[450] cursor-pointer"
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
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
              History
            </button>
          </div>
        )}
      </div>

      {canonical && open && (
        <ExtractionSummary
          accepted={accepted}
          summary={summarizeFieldStates(extraction.field_confidence)}
        />
      )}
    </div>
  );
}
