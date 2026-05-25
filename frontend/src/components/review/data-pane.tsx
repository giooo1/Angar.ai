"use client";

import type { ExtractionStatusResponse } from "@/lib/api-types";
import type { CanonicalInvoice } from "@/lib/canonical";

import { DocumentStrip } from "./document-strip";
import { FlagsBlock } from "./flags-block";
import { LineItemsTable } from "./line-items-table";
import { NotesPanel } from "./notes-panel";
import { PartyBlock } from "./party-block";
import { ReviewHeader } from "./review-header";
import { RiskStrip } from "./risk-strip";
import { TotalsBlock } from "./totals-block";

type Props = {
  data: ExtractionStatusResponse;
  /** The live draft canonical (display values source from here so a fresh
   *  mount — split pane or fullscreen drawer — reflects prior edits). */
  canonical: CanonicalInvoice;
  confidence: Record<string, number>;
  overall: number | null;
  buckets: { high: number; med: number; low: number };
  dirty: boolean;
  onSave: () => Promise<void>;
};

/**
 * The extracted-data surface: a sticky action header followed by the
 * Document / Seller / Buyer / Line items / Totals / Flags / Notes blocks.
 * Mounted in the side-by-side layout and (WS3) in the fullscreen drawer —
 * both inside the same edit provider, so edits sync through the shared draft.
 */
export function DataPane({ data, canonical, confidence, overall, buckets, dirty, onSave }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <ReviewHeader
        documentId={data.document_id}
        extractionId={data.extraction_id}
        approvedAt={data.approved_at}
        filenameBase={canonical.document_number ?? "export"}
        dirty={dirty}
        onSave={onSave}
        accepted={canonical.accepted}
        overall={overall}
      />
      <RiskStrip high={buckets.high} med={buckets.med} low={buckets.low} />
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
    </div>
  );
}
