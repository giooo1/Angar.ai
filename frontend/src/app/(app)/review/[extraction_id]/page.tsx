"use client";

import { useParams } from "next/navigation";

import { ExtractionErrorCard } from "@/components/review/extraction-error-card";
import { FileBar } from "@/components/review/file-bar";
import { PdfPane } from "@/components/review/pdf-pane";
import { ReviewBody } from "@/components/review/review-body";
import { useExtraction } from "@/hooks/use-extraction";
import { documentFileUrl } from "@/lib/api";

/**
 * Review v2 — confidence-first.
 *
 * Left: sticky PDF pane with a zoom toolbar (buttons visual-only for v1).
 * Right: the editable <ReviewBody> — acceptance banner → risk strip →
 *        Document / Seller / Buyer / Line items / Totals / Flags / Notes
 *        → sticky action bar with Save / Approve / Export.
 *
 * The screen shows `corrected_data` when the user has saved edits, else the
 * model's raw `canonical_data`. Failed extractions render
 * `<ExtractionErrorCard>` instead of the body.
 */
export default function ReviewDetailPage() {
  const params = useParams<{ extraction_id: string }>();
  const extractionId = params?.extraction_id ?? null;
  const { data, isLoading, error, phase } = useExtraction(extractionId);

  if (error) {
    return (
      <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
        <div className="bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-xl p-5">
          <p className="font-serif text-[17px] font-medium m-0 mb-1">
            Couldn&apos;t load this extraction
          </p>
          <p className="m-0 text-[13px]">{error}</p>
        </div>
      </main>
    );
  }

  if (isLoading || !data) {
    return (
      <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
        <div className="bg-paper border border-line rounded-xl p-12 text-center text-ink-3">
          {phase === "polling" ? (
            <>
              <p className="font-serif text-[20px] font-medium text-ink m-0 mb-1.5">
                Extracting…
              </p>
              <p className="m-0 text-[13px]">
                Claude is reading the document. Usually finishes in 5–25 seconds.
              </p>
            </>
          ) : (
            <p className="m-0 text-[13px]">Loading…</p>
          )}
        </div>
      </main>
    );
  }

  // Show reviewer corrections when present, else the model's raw output.
  const canonical = data.corrected_data ?? data.canonical_data;

  return (
    <main className="px-8 py-6 pb-2 w-full max-w-[1480px]">
      <FileBar extraction={data} canonical={canonical} />

      <div className="grid grid-cols-[1fr_1fr] gap-4 items-start">
        <PdfPane
          url={documentFileUrl(data.document_id)}
          filename={canonical?.extraction.source_filename ?? "document"}
        />

        {canonical ? (
          <ReviewBody data={data} canonical={canonical} />
        ) : (
          <ExtractionErrorCard
            errorCode={data.error_code}
            errorMessage={data.error_message}
          />
        )}
      </div>
    </main>
  );
}
