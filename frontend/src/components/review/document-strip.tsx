import { ConfidenceRow } from "./confidence-row";
import { SectionBlock } from "./section-block";

type Props = {
  extractionId: string;
  documentNumber: string | null;
  documentDate: string | null;
  currency: string;
  confidence: Record<string, number>;
};

/**
 * Document identity section: Number / Date / Currency as full-width stacked
 * rows (same row style as Seller/Buyer), each with its own two-axis state
 * chip. The header carries the "D" badge; no document-type adornment.
 */
export function DocumentStrip({
  extractionId,
  documentNumber,
  documentDate,
  currency,
  confidence,
}: Props) {
  return (
    <SectionBlock letter="D" title="Document">
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath="document_number"
        label="Number"
        value={documentNumber}
        confidence={confidence["document_number"]}
      />
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath="document_date"
        label="Date"
        value={documentDate}
        confidence={confidence["document_date"]}
      />
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath="document_currency"
        label="Currency"
        value={currency}
        confidence={confidence["document_currency"]}
      />
    </SectionBlock>
  );
}
