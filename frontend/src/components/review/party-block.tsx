import type { Party } from "@/lib/canonical";
import { ConfidenceRow } from "./confidence-row";
import { SectionHeader } from "./section-header";

type Props = {
  /** Either "seller" or "buyer" — also the field-path prefix. */
  side: "seller" | "buyer";
  title: string;
  party: Party | null;
  confidence: Record<string, number>;
  extractionId: string;
};

const SCRIPT_LABEL: Record<string, string> = {
  mkhedruli: "Mkhedruli",
  latin: "Latin",
  mixed: "Latin + Mkhedruli",
  unknown: "Mixed",
};

/**
 * Seller / Buyer as a flat two-column grid:
 *   left  → Name, Party type
 *   right → TIN, Address
 * The header keeps the right-aligned script indicator.
 */
export function PartyBlock({ side, title, party, confidence }: Props) {
  const scriptLabel = party?.script ? SCRIPT_LABEL[party.script] ?? "Mixed" : "Mixed";
  const nameMkhedruli = party?.script === "mkhedruli" || party?.script === "mixed";

  return (
    <section>
      <SectionHeader label={title} right={<ScriptChip label={scriptLabel} />} />
      {/* Row-major fill: Name, TIN, Party type, Address → left col Name/Party type, right col TIN/Address. */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-[18px]">
        <ConfidenceRow
          fieldPath={`${side}.name`}
          label="Name"
          value={party?.name ?? null}
          confidence={confidence[`${side}.name`]}
          valueClassName={nameMkhedruli ? "font-serif italic text-accent" : undefined}
        />
        <ConfidenceRow
          fieldPath={`${side}.tin`}
          label="TIN"
          value={party?.tin ?? null}
          confidence={confidence[`${side}.tin`]}
          numeric
        />
        <ConfidenceRow
          fieldPath={`${side}.party_type`}
          label="Party type"
          value={partyTypeLabel(party?.party_type)}
          confidence={confidence[`${side}.party_type`]}
          editable={false}
        />
        <ConfidenceRow
          fieldPath={`${side}.address`}
          label="Address"
          value={party?.address ?? null}
          confidence={confidence[`${side}.address`]}
        />
      </div>
    </section>
  );
}

function ScriptChip({ label }: { label: string }) {
  return (
    <span className="text-[10px] text-ink-3 tracking-[0.04em] lowercase">
      {label.toLowerCase()}
    </span>
  );
}

function partyTypeLabel(t: Party["party_type"] | undefined): string | null {
  switch (t) {
    case "legal_entity":
      return "Legal entity";
    case "individual_ge":
      return "Individual";
    case "foreign_person":
      return "Foreign person";
    default:
      return null;
  }
}
