import Link from "next/link";

import type { CanonicalInvoice } from "@/lib/canonical";
import type { ExtractionStatusResponse } from "@/lib/api-types";

type Props = {
  extraction: ExtractionStatusResponse;
  canonical: CanonicalInvoice | null;
};

/**
 * Simpler top bar for Review v2: back arrow + thumb + filename + a
 * single subtitle line. Status chips and re-extract have moved to the
 * right pane (acceptance banner + action bar) per the new spec.
 */
export function FileBar({ extraction, canonical }: Props) {
  const filename = canonical?.extraction.source_filename ?? "(unknown filename)";
  const ms = extraction.processing_time_ms ?? 0;
  const sec = ms > 0 ? (ms / 1000).toFixed(1) : null;
  const sub = [
    sec ? `extracted ${sec}s` : null,
    "1 page",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3 bg-paper border border-line rounded-xl mb-4">
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
        <span
          className="doc-thumb flex-shrink-0"
          style={{ width: 30, height: 38 }}
        />
        <div className="min-w-0">
          <div className="font-serif text-[16.5px] font-medium tracking-[-0.015em] text-ink overflow-hidden text-ellipsis whitespace-nowrap leading-tight">
            {filename}
          </div>
          <div className="font-mono text-[11px] text-ink-3 tracking-[0.04em] mt-0.5">
            {sub}
          </div>
        </div>
      </div>
    </div>
  );
}
