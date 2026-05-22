import { Button } from "@/components/ui/button";
import type { CanonicalInvoice } from "@/lib/canonical";

type Props = {
  canonical: CanonicalInvoice | null;
  promptVersion: string;
  modelVersion: string;
};

/**
 * Sticky bottom bar with summary info + (stubbed) Approve / Export
 * buttons. Editing is a future step; for now these are visually
 * present but disabled so the demo accountant sees the intent.
 */
export function ActionBar({ canonical, promptVersion, modelVersion }: Props) {
  const fieldCount = canonical ? countFields(canonical) : 0;
  return (
    <div className="sticky bottom-0 bg-gradient-to-t from-bg from-70% to-transparent py-4 pt-4 mt-1.5 flex items-center justify-between gap-4">
      <div className="font-mono text-[11px] text-ink-3 tracking-[0.04em]">
        {fieldCount} fields · prompt {promptVersion} · {modelVersion}
      </div>
      <div className="flex gap-2 items-center">
        <Button variant="ghost" disabled title="Discarding changes lands when editing does (step 5)">
          Discard
        </Button>
        <Button variant="secondary" disabled title="Export lands with Dashboard (step 7)">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          >
            <path d="M12 4v12m0 0l-4-4m4 4l4-4M4 20h16" />
          </svg>
          Export
        </Button>
        <Button
          variant="accent"
          disabled
          title="Approve writes a verification record (lands with corrections)"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12l5 5L20 7" />
          </svg>
          Approve
        </Button>
      </div>
    </div>
  );
}

/** Rough "non-null leaf fields" count — purely for the human eye in the footer. */
function countFields(c: CanonicalInvoice): number {
  let n = 0;
  if (c.document_number) n++;
  if (c.document_date) n++;
  if (c.document_currency) n++;
  if (c.seller) n += partyFields(c.seller);
  if (c.buyer) n += partyFields(c.buyer);
  n += c.items.length * 4; // description + quantity + unit_price + total
  for (const field of [
    c.subtotal_total,
    c.vat_total,
    c.discount_total,
    c.shipping_cost,
    c.grand_total,
  ]) {
    if (field) n++;
  }
  if (c.vat_treatment_reason) n++;
  if (c.transport) n += 4;
  n += c.extraction_notes.length;
  return n;
}

function partyFields(p: {
  tin: string | null;
  address: string | null;
  bank_account: string | null;
}): number {
  let n = 1; // name always
  if (p.tin) n++;
  if (p.address) n++;
  if (p.bank_account) n++;
  return n;
}
