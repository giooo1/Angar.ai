"use client";

import type { ExtractionStatusResponse } from "@/lib/api-types";
import type { CanonicalInvoice } from "@/lib/canonical";
import { countNeedsReview } from "@/lib/confidence";

import { DocumentStrip } from "./document-strip";
import { FlagsBlock } from "./flags-block";
import { LineItemsTable } from "./line-items-table";
import { NotesPanel } from "./notes-panel";
import { PartyBlock } from "./party-block";
import { ReviewHeader } from "./review-header";
import { TotalsBlock } from "./totals-block";

type Props = {
  data: ExtractionStatusResponse;
  /** Live draft canonical (display values source here so a fresh mount — split
   *  pane or fullscreen drawer — reflects prior edits). */
  canonical: CanonicalInvoice;
  confidence: Record<string, number>;
  overall: number | null;
  dirty: boolean;
  onSave: () => Promise<void>;
};

/**
 * Flat white data surface: a sticky header, then Document / Seller / Buyer /
 * Line items / Totals / Flags / Notes separated by hairline dividers — no
 * inner cards, no badges, no per-field pills.
 */
export function DataPane({ data, canonical, confidence, overall, dirty, onSave }: Props) {
  return (
    <div className="bg-paper border border-line rounded-xl px-4 pb-4">
      <ReviewHeader
        documentId={data.document_id}
        extractionId={data.extraction_id}
        approvedAt={data.approved_at}
        filenameBase={canonical.document_number ?? "export"}
        dirty={dirty}
        onSave={onSave}
        accepted={canonical.accepted}
        overall={overall}
        needsReview={countNeedsReview(confidence)}
      />
      <div className="[&>section]:py-5 [&>section]:border-t [&>section]:border-line-2 [&>section:first-child]:border-t-0 [&>section:first-child]:pt-1">
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
          party={canonical.seller}
          confidence={confidence}
          extractionId={data.extraction_id}
        />
        <PartyBlock
          side="buyer"
          title="Buyer"
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
      </div>
    </div>
  );
}
