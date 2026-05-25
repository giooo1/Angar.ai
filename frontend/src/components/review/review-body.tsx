"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import type { ExtractionStatusResponse } from "@/lib/api-types";
import type { CanonicalInvoice } from "@/lib/canonical";
import { saveCorrections } from "@/lib/api";
import { countByBucket, meanConfidence } from "@/lib/confidence";

import { AcceptanceBanner } from "./acceptance-banner";
import { DocumentStrip } from "./document-strip";
import { FlagsBlock } from "./flags-block";
import { LineItemsTable } from "./line-items-table";
import { NotesPanel } from "./notes-panel";
import { PartyBlock } from "./party-block";
import {
  ReviewEditProvider,
  setByPath,
  type ReviewEditContextValue,
} from "./review-edit-context";
import { ReviewActionBar } from "./review-action-bar";
import { RiskStrip } from "./risk-strip";
import { TotalsBlock } from "./totals-block";

type Props = {
  data: ExtractionStatusResponse;
  /** Effective canonical (corrected over raw) — guaranteed non-null by caller. */
  canonical: CanonicalInvoice;
};

/**
 * Right pane of the review screen, plus the edit/save plumbing.
 *
 * Field rows and table cells stay uncontrolled `contentEditable`; on blur
 * they push their text into `draftRef` via the edit context. `dirty` flips
 * so the action bar can enable Save. Saving PUTs the whole draft as the
 * corrected canonical — the model's raw output is preserved server-side.
 *
 * The `value` props feeding the editable nodes come from `canonical` and
 * never change, so re-renders (e.g. toggling `dirty`) don't clobber the
 * caret or the user's in-progress edits.
 */
export function ReviewBody({ data, canonical }: Props) {
  const confidence = data.field_confidence ?? {};
  const overall = meanConfidence(confidence);
  const buckets = countByBucket(confidence);

  const draftRef = useRef<CanonicalInvoice | null>(null);
  if (draftRef.current === null) {
    draftRef.current = structuredClone(canonical);
  }
  const [dirty, setDirty] = useState(false);

  const onSave = useCallback(async () => {
    if (draftRef.current) {
      await saveCorrections(data.extraction_id, draftRef.current);
      setDirty(false);
    }
  }, [data.extraction_id]);

  const ctx = useMemo<ReviewEditContextValue>(
    () => ({
      editable: true,
      updateField: (path, value) => {
        if (draftRef.current) {
          setByPath(draftRef.current as unknown as Record<string, unknown>, path, value);
          setDirty(true);
        }
      },
      updateItem: (index, key, value) => {
        const item = draftRef.current?.items?.[index];
        if (item) {
          setByPath(item as unknown as Record<string, unknown>, key, value);
          setDirty(true);
        }
      },
    }),
    [],
  );

  return (
    <ReviewEditProvider value={ctx}>
      <div className="flex flex-col gap-3.5">
        <AcceptanceBanner
          accepted={canonical.accepted}
          rejectionReason={canonical.rejection_reason}
          overall={overall}
          confidentCount={buckets.high}
          needsReviewCount={buckets.med + buckets.low}
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
        <ReviewActionBar
          documentId={data.document_id}
          extractionId={data.extraction_id}
          approvedAt={data.approved_at}
          filenameBase={canonical.document_number ?? "export"}
          dirty={dirty}
          onSave={onSave}
        />
      </div>
    </ReviewEditProvider>
  );
}
