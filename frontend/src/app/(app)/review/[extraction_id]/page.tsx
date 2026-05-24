"use client";

import { useParams } from "next/navigation";

import { AcceptanceBanner } from "@/components/review/acceptance-banner";
import { DocumentStrip } from "@/components/review/document-strip";
import { ExtractionErrorCard } from "@/components/review/extraction-error-card";
import { FileBar } from "@/components/review/file-bar";
import { FlagsBlock } from "@/components/review/flags-block";
import { LineItemsTable } from "@/components/review/line-items-table";
import { NotesPanel } from "@/components/review/notes-panel";
import { PartyBlock } from "@/components/review/party-block";
import { PdfPane } from "@/components/review/pdf-pane";
import { ReviewActionBar } from "@/components/review/review-action-bar";
import { RiskStrip } from "@/components/review/risk-strip";
import { TotalsBlock } from "@/components/review/totals-block";
import { useExtraction } from "@/hooks/use-extraction";
import { documentFileUrl } from "@/lib/api";
import { countByBucket, meanConfidence } from "@/lib/confidence";

/**
 * Review v2 — confidence-first.
 *
 * Left: sticky PDF pane with a zoom toolbar (buttons visual-only for v1).
 * Right: acceptance banner → risk strip → Document / Seller / Buyer
 *        / Line items / Totals / Flags / Notes → sticky action bar.
 *
 * Per-field confidence comes from `data.field_confidence` (backend
 * heuristic, WS2). The risk strip counts each field into high/med/low
 * buckets so the user can scan for what needs attention at a glance.
 *
 * Failed extractions still render `<ExtractionErrorCard>` for the
 * right pane (unchanged from WS2).
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
  const confidence = data.field_confidence ?? {};
  const overall = meanConfidence(confidence);
  const buckets = countByBucket(confidence);

  return (
    <main className="px-8 py-6 pb-2 w-full max-w-[1480px]">
      <FileBar extraction={data} canonical={canonical} />

      <div className="grid grid-cols-[1fr_1fr] gap-4 items-start">
        <PdfPane
          url={documentFileUrl(data.document_id)}
          filename={canonical?.extraction.source_filename ?? "document"}
        />

        {canonical ? (
          <div className="flex flex-col gap-3.5">
            <AcceptanceBanner
              accepted={canonical.accepted}
              rejectionReason={canonical.rejection_reason}
              overall={overall}
              confidentCount={buckets.high}
              needsReviewCount={buckets.med + buckets.low}
            />
            <RiskStrip
              high={buckets.high}
              med={buckets.med}
              low={buckets.low}
            />
            <DocumentStrip
              extractionId={data.extraction_id}
              documentNumber={canonical.document_number}
              documentDate={canonical.document_date}
              currency={canonical.document_currency}
              confidence={confidence}
            />
            <PartyBlock
              side="seller"
              title="Seller"
              letter="S"
              party={canonical.seller}
              confidence={confidence}
              extractionId={data.extraction_id}
            />
            <PartyBlock
              side="buyer"
              title="Buyer"
              letter="B"
              party={canonical.buyer}
              confidence={confidence}
              extractionId={data.extraction_id}
            />
            <LineItemsTable items={canonical.items} />
            <TotalsBlock
              extractionId={data.extraction_id}
              subtotal={canonical.subtotal_total}
              vat={canonical.vat_total}
              discount={canonical.discount_total}
              shipping={canonical.shipping_cost}
              grand={canonical.grand_total}
              confidence={confidence}
            />
            <FlagsBlock canonical={canonical} />
            <NotesPanel
              notes={canonical.extraction_notes}
              warnings={data.warnings}
              vatTreatmentReason={canonical.vat_treatment_reason}
              rejectionReason={canonical.rejection_reason}
            />
            <ReviewActionBar documentId={data.document_id} />
          </div>
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
