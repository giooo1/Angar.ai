"use client";

import { useParams } from "next/navigation";

import { FileBar } from "@/components/review/file-bar";
import { ReviewWorkspace } from "@/components/review/review-workspace";
import { useExtraction } from "@/hooks/use-extraction";

/**
 * Review screen — document-first.
 *
 * A top file bar over the <ReviewWorkspace>, which owns the responsive
 * document/data layout, the react-pdf viewer, the editable data pane with its
 * sticky action header, and the edit draft. The screen prefers
 * `corrected_data` (reviewer edits) over the model's raw `canonical_data`;
 * failed extractions render an error card in the data slot.
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

  const canonical = data.corrected_data ?? data.canonical_data;

  return (
    <main className="px-8 py-6 pb-2 w-full max-w-[1480px]">
      <FileBar extraction={data} canonical={canonical} />
      <ReviewWorkspace data={data} />
    </main>
  );
}
