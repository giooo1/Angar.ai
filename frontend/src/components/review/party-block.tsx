import { ConfidenceRow } from "./confidence-row";
import { SectionBlock } from "./section-block";
import type { Party } from "@/lib/canonical";

type Props = {
  /** Either "seller" or "buyer" — also the field-path prefix. */
  side: "seller" | "buyer";
  /** Sentence-cased title rendered in the section header (e.g. "Seller"). */
  title: string;
  /** Single-letter index in the header chip. */
  letter: string;
  party: Party | null;
  confidence: Record<string, number>;
  extractionId: string;
};

/**
 * Reusable card for Seller and Buyer. Reads the `Party` and renders
 * Name, Name (en) (if present), TIN, Party type, Address (full-width).
 * The script chip in the header reflects the canonical's `script` enum.
 */
export function PartyBlock({
  side,
  title,
  letter,
  party,
  confidence,
  extractionId,
}: Props) {
  return (
    <SectionBlock letter={letter} title={title}>
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath={`${side}.name`}
        label="Name"
        value={party?.name ?? null}
        confidence={confidence[`${side}.name`]}
        valueClassName={
          party?.script === "mkhedruli" || party?.script === "mixed"
            ? "!font-serif !italic !text-accent text-[15px] !font-normal"
            : undefined
        }
      />
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath={`${side}.tin`}
        label="TIN"
        value={party?.tin ?? null}
        confidence={confidence[`${side}.tin`]}
      />
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath={`${side}.party_type`}
        label="Party type"
        value={partyTypeLabel(party?.party_type)}
        confidence={confidence[`${side}.party_type`]}
        present={!!party}
        editable={false}
      />
      <ConfidenceRow
        extractionId={extractionId}
        fieldPath={`${side}.address`}
        label="Address"
        value={party?.address ?? null}
        confidence={confidence[`${side}.address`]}
        full
      />
    </SectionBlock>
  );
}

function partyTypeLabel(t: Party["party_type"] | undefined): string {
  switch (t) {
    case "legal_entity":
      return "Legal entity";
    case "individual_ge":
      return "Individual";
    case "foreign_person":
      return "Foreign person";
    case "unknown":
    case undefined:
      return "—";
  }
}
