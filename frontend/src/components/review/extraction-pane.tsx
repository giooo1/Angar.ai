import { Chip } from "@/components/ui/chip";
import type { CanonicalInvoice, Party, TransportInfo } from "@/lib/canonical";
import { FieldRow } from "./field-row";
import { LineItemsTable } from "./line-items-table";
import { moneyText } from "./money-cell";
import { NotesPanel } from "./notes-panel";
import { Section } from "./section";

type Props = { canonical: CanonicalInvoice };

/**
 * Right pane of the Review screen — every field of the CanonicalInvoice
 * laid out as a stack of Section cards. Read-only in step 4; click-to-edit
 * lands later.
 */
export function ExtractionPane({ canonical }: Props) {
  const c = canonical;
  return (
    <div className="flex flex-col gap-3.5">
      <AcceptanceBanner canonical={c} />

      <PartySection party={c.seller} title="Seller" />
      <PartySection party={c.buyer} title="Buyer" />

      <Section badge="D" title="Document">
        <FieldRow label="Number" value={c.document_number} mono />
        <FieldRow label="Date" value={c.document_date} mono />
        <FieldRow label="Currency" value={c.document_currency} mono />
        {c.references_other_document && (
          <FieldRow label="References" value={c.references_other_document} mono />
        )}
      </Section>

      <LineItemsTable items={c.items} />

      <Section badge="₾" title="Amounts">
        <FieldRow label="Subtotal" value={moneyText(c.subtotal_total)} mono />
        <FieldRow label="VAT" value={moneyText(c.vat_total)} mono />
        <FieldRow label="Discount" value={moneyText(c.discount_total)} mono />
        <FieldRow label="Shipping" value={moneyText(c.shipping_cost)} mono />
        <FieldRow
          label="Grand total"
          value={moneyText(c.grand_total)}
          emphasis
        />
      </Section>

      <FlagsSection canonical={c} />

      {c.transport && <TransportSection transport={c.transport} />}

      <NotesPanel
        notes={c.extraction_notes}
        warnings={c.extraction.warnings ?? []}
        vatTreatmentReason={c.vat_treatment_reason}
        rejectionReason={c.rejection_reason}
      />
    </div>
  );
}

function AcceptanceBanner({ canonical }: { canonical: CanonicalInvoice }) {
  const accepted = canonical.accepted;
  const fields = canonical.extraction.field_confidence;
  const overallConf =
    Object.keys(fields).length > 0
      ? Object.values(fields).reduce((a, b) => a + b, 0) / Object.values(fields).length
      : null;

  return (
    <div
      className={
        "flex items-start justify-between gap-3.5 px-4 py-3.5 rounded-xl border " +
        (accepted
          ? "bg-accent-soft border-[rgba(45,106,79,0.18)] text-accent"
          : "bg-error-soft border-[rgba(184,52,47,0.25)] text-[#7a201d]")
      }
    >
      <div className="flex items-start gap-2.5 min-w-0">
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="mt-0.5 flex-shrink-0"
        >
          {accepted ? (
            <>
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
              <path d="M22 4L12 14.01l-3-3" />
            </>
          ) : (
            <>
              <circle cx="12" cy="12" r="10" />
              <path d="M15 9l-6 6M9 9l6 6" />
            </>
          )}
        </svg>
        <div>
          <p className="font-serif text-[15.5px] font-medium tracking-[-0.01em] leading-tight m-0 mb-1">
            {accepted ? "Looks extractable" : "Not extractable as an invoice"}
          </p>
          <p className="text-[12px] m-0 opacity-90">
            {accepted
              ? `${canonical.items.length} line ${canonical.items.length === 1 ? "item" : "items"} parsed.`
              : canonical.rejection_reason ?? "See rejection reason below."}
          </p>
        </div>
      </div>
      {overallConf !== null && (
        <span
          className="font-mono text-[11px] px-2.5 py-1 rounded-full bg-paper border border-[rgba(45,106,79,0.2)] inline-flex items-center gap-1.5 flex-shrink-0"
        >
          conf · <b className="text-accent font-semibold">{(overallConf * 100).toFixed(1)}%</b>
        </span>
      )}
    </div>
  );
}

function PartySection({ party, title }: { party: Party | null; title: string }) {
  return (
    <Section badge={title[0]} title={title}>
      <FieldRow
        label="Name"
        value={party?.name ?? null}
        geo={party?.script === "mkhedruli" || party?.script === "mixed"}
      />
      <FieldRow label="TIN" value={party?.tin ?? null} mono />
      <FieldRow label="TIN labeled" value={party?.tin_label_present ? "yes" : party ? "no" : null} mono />
      <FieldRow label="Type" value={party?.party_type ?? null} mono />
      <FieldRow label="Script" value={party?.script ?? null} mono />
      <FieldRow label="Address" value={party?.address ?? null} />
      <FieldRow label="Bank" value={party?.bank_account ?? null} mono />
    </Section>
  );
}

function FlagsSection({ canonical }: { canonical: CanonicalInvoice }) {
  const flags: { label: string; on: boolean; variant?: "warn" | "default" }[] = [
    { label: "VAT invoice", on: canonical.is_vat_invoice },
    { label: "Reverse VAT", on: canonical.is_reverse_vat },
    { label: "Free of charge", on: canonical.is_free_of_charge },
    { label: "Contains PII", on: canonical.contains_pii_beyond_parties, variant: "warn" },
  ];
  return (
    <Section badge="!" title="Flags">
      <div className="px-4 py-3.5 flex flex-wrap gap-2">
        {flags.map((f) => (
          <Chip
            key={f.label}
            variant={f.on ? (f.variant ?? "green") : "default"}
            dot={f.on}
          >
            {f.label}
          </Chip>
        ))}
        <Chip variant="default">
          VAT: {canonical.vat_treatment_overall}
        </Chip>
      </div>
    </Section>
  );
}

function TransportSection({ transport: t }: { transport: TransportInfo }) {
  return (
    <Section badge="T" title="Transport">
      <FieldRow label="From" value={t.start_address ?? null} />
      <FieldRow label="To" value={t.end_address ?? null} />
      <FieldRow label="Plate" value={t.vehicle_plate ?? null} mono />
      <FieldRow
        label="Has trailer"
        value={t.has_trailer === null ? null : t.has_trailer ? "yes" : "no"}
        mono
      />
      <FieldRow label="Begin" value={t.begin_date ?? null} mono />
      <FieldRow label="Delivery" value={t.delivery_date ?? null} mono />
      <FieldRow
        label="Cost"
        value={moneyText(t.transport_cost)}
        mono
      />
      <FieldRow label="Cost payer" value={t.transport_cost_payer ?? null} mono />
      {t.driver && (
        <>
          <FieldRow
            label="Driver"
            value={t.driver.name}
            geo={t.driver.script === "mkhedruli" || t.driver.script === "mixed"}
          />
          <FieldRow label="Driver ID" value={t.driver.tin ?? null} mono />
        </>
      )}
    </Section>
  );
}
