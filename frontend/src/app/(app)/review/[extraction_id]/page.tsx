"use client";

import { useParams } from "next/navigation";

import { ActionBar } from "@/components/review/action-bar";
import { ExtractionPane } from "@/components/review/extraction-pane";
import { FileBar } from "@/components/review/file-bar";
import { PdfPane } from "@/components/review/pdf-pane";
import { useExtraction } from "@/hooks/use-extraction";
import { documentFileUrl } from "@/lib/api";

/**
 * Review screen for a single extraction.
 *
 * Layout per App.html `<section data-screen="review">`:
 *   FileBar              (filename + status + re-extract)
 *   two-pane grid:
 *     PdfPane            (iframe of the original PDF — left)
 *     ExtractionPane     (all CanonicalInvoice fields — right)
 *   ActionBar            (sticky bottom; stubbed Approve/Export)
 *
 * Read-only in step 4. Corrections + Export come later.
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

  const canonical = data.canonical_data;

  return (
    <main className="px-10 py-6 pb-2 w-full max-w-[1480px]">
      <FileBar extraction={data} canonical={canonical} />

      <div className="grid grid-cols-[1fr_1.05fr] gap-4 items-start">
        <PdfPane
          url={documentFileUrl(data.document_id)}
          filename={canonical?.extraction.source_filename ?? "document"}
        />
        {canonical ? (
          <ExtractionPane canonical={canonical} />
        ) : (
          <div className="bg-paper border border-line rounded-xl p-6 text-ink-3 text-[13px]">
            <p className="font-serif text-[17px] font-medium text-ink m-0 mb-2">
              No structured data yet
            </p>
            <p className="m-0">
              {data.error_message ??
                "This extraction returned no canonical_data — likely a parse failure."}
            </p>
          </div>
        )}
      </div>

      <ActionBar
        canonical={canonical}
        promptVersion={data.prompt_version}
        modelVersion={data.model_version}
      />
    </main>
  );
}
