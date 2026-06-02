"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  createBillingPortalSession,
  createCheckoutSession,
  type Plan,
} from "@/lib/api";
import { ApiError } from "@/lib/api-types";

type Tile = {
  /** Internal plan key (unchanged — maps to the Stripe price id). */
  slug: Plan;
  label: string;
  priceKa: string;
  priceEn: string;
  quotaKa: string;
  quotaEn: string;
  features: string[];
  mostPopular?: boolean;
};

// Customer-facing tiers. Internal keys are legacy: `pro` shows as "Solo",
// `business` as "Pro" (keeps checkout → Stripe price-id mapping intact).
const TILES: Tile[] = [
  {
    slug: "pro",
    label: "Solo",
    priceKa: "₾49 / თვეში",
    priceEn: "₾49 / month",
    quotaKa: "100 ექსტრაქცია / თვეში",
    quotaEn: "100 extractions / month",
    features: [
      "PDF, JPG, PNG, HEIC",
      "Mkhedruli + Latin OCR",
      "CSV, JSON, Excel export",
      "Email support",
    ],
  },
  {
    slug: "business",
    label: "Pro",
    priceKa: "₾149 / თვეში",
    priceEn: "₾149 / month",
    quotaKa: "500 ექსტრაქცია / თვეში",
    quotaEn: "500 extractions / month",
    features: [
      "Everything in Solo, plus:",
      "Bulk upload up to 100 files",
      "Priority extraction queue",
      "API access (beta)",
      "Priority email support",
    ],
    mostPopular: true,
  },
];

export function BillingPlans({
  currentPlan,
  emailVerified,
}: {
  currentPlan: string;
  emailVerified: boolean;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ctaDisabled = !emailVerified;
  const disabledReason = ctaDisabled ? "Verify your email to enable billing." : null;

  const upgrade = async (plan: Plan) => {
    setBusy(plan);
    setError(null);
    try {
      const { url } = await createCheckoutSession(plan);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.messageEn : "Could not start checkout.");
      setBusy(null);
    }
  };

  const openPortal = async () => {
    setBusy("portal");
    setError(null);
    try {
      const { url } = await createBillingPortalSession();
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.messageEn : "Could not open the billing portal.");
      setBusy(null);
    }
  };

  return (
    <>
      {currentPlan === "free" && (
        <p className="m-0 mb-4 text-[13px] text-ink-3">
          თქვენ ხართ <span className="font-medium text-ink">Free</span> გეგმაზე · 25/თვე{" "}
          <span className="text-ink-4">· You&apos;re on the Free plan · 25/mo</span>
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
        {TILES.map((tile) => {
          const isCurrent = tile.slug === currentPlan;
          return (
            <PlanTile
              key={tile.slug}
              tile={tile}
              isCurrent={isCurrent}
              ctaDisabled={ctaDisabled || isCurrent}
              disabledReason={isCurrent ? null : disabledReason}
              onUpgrade={() => upgrade(tile.slug)}
              busy={busy === tile.slug}
            />
          );
        })}
      </div>

      {error && (
        <div className="mt-5 bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-md px-3 py-2 text-[12.5px]">
          {error}
        </div>
      )}

      {currentPlan !== "free" && (
        <div className="mt-7 pt-5 border-t border-line-2">
          <Button
            variant="secondary"
            type="button"
            onClick={openPortal}
            disabled={busy === "portal"}
          >
            {busy === "portal" ? "Opening…" : "Manage subscription"}
          </Button>
          <p className="m-0 mt-2 text-[12.5px] text-ink-3">
            Opens the Stripe-hosted customer portal — change card, switch plan, or cancel.
          </p>
        </div>
      )}
    </>
  );
}

function PlanTile({
  tile,
  isCurrent,
  ctaDisabled,
  disabledReason,
  onUpgrade,
  busy,
}: {
  tile: Tile;
  isCurrent: boolean;
  ctaDisabled: boolean;
  disabledReason: string | null;
  onUpgrade: () => void;
  busy: boolean;
}) {
  return (
    <div
      className={cn(
        "relative bg-paper border rounded-xl p-6 flex flex-col gap-3",
        isCurrent
          ? "border-accent shadow-[0_0_0_3px_var(--color-accent-soft)]"
          : tile.mostPopular
            ? "border-accent-2"
            : "border-line",
      )}
    >
      {tile.mostPopular && !isCurrent && (
        <span className="absolute -top-2.5 left-6 bg-accent text-white font-mono text-[9.5px] tracking-[0.06em] uppercase px-2 py-0.5 rounded-full">
          Most popular
        </span>
      )}

      <div className="flex items-baseline justify-between">
        <h3 className="font-serif text-[20px] m-0 tracking-[-0.015em] font-normal">{tile.label}</h3>
        {isCurrent && (
          <span className="font-mono text-[10px] text-accent tracking-[0.06em] uppercase">Current</span>
        )}
      </div>

      <div>
        <div className="font-serif text-[26px] tracking-[-0.02em] text-ink leading-none">
          {tile.priceKa}
        </div>
        <div className="text-[12px] text-ink-3 mt-1">{tile.priceEn}</div>
      </div>

      <div className="font-mono text-[11px] text-ink-2 tracking-[0.04em]">
        {tile.quotaKa}
        <span className="block text-ink-3">{tile.quotaEn}</span>
      </div>

      <ul className="m-0 mt-1 p-0 list-none flex flex-col gap-1.5">
        {tile.features.map((f) =>
          f.endsWith(":") ? (
            <li key={f} className="text-[12.5px] text-ink font-medium mt-1">
              {f}
            </li>
          ) : (
            <li key={f} className="flex items-start gap-2 text-[13px] text-ink-2">
              <span className="text-accent-2 mt-0.5">✓</span>
              {f}
            </li>
          ),
        )}
      </ul>

      <div className="mt-auto pt-2">
        <Button
          variant={isCurrent ? "secondary" : "primary"}
          type="button"
          onClick={onUpgrade}
          disabled={ctaDisabled || busy}
          className="w-full justify-center"
        >
          {busy ? "Opening…" : isCurrent ? "Current plan" : `Upgrade to ${tile.label}`}
        </Button>
        {disabledReason && (
          <p className="m-0 mt-2 text-[11.5px] text-ink-3">{disabledReason}</p>
        )}
      </div>
    </div>
  );
}
