import { ConfidenceRow } from "./confidence-row";
import { SectionHeader } from "./section-header";

type Props = {
  extractionId: string;
  documentNumber: string | null;
  documentDate: string | null;
  currency: string;
  confidence: Record<string, number>;
};

/**
 * Document identity: Number / Date / Currency in three short columns.
 * `extractionId` is accepted for call-site symmetry but no longer used.
 */
export function DocumentStrip({
  documentNumber,
  documentDate,
  currency,
  confidence,
}: Props) {
  return (
    <section>
      <SectionHeader label="Document" />
      <div className="grid grid-cols-3 gap-x-6">
        <ConfidenceRow
          fieldPath="document_number"
          label="Number"
          value={documentNumber}
          confidence={confidence["document_number"]}
          numeric
        />
        <ConfidenceRow
          fieldPath="document_date"
          label="Date"
          value={documentDate}
          confidence={confidence["document_date"]}
          numeric
        />
        <ConfidenceRow
          fieldPath="document_currency"
          label="Currency"
          value={currency}
          confidence={confidence["document_currency"]}
        />
      </div>
    </section>
  );
}
