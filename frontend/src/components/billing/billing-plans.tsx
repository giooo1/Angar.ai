"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  createBillingPortalSession,
  createCheckoutSession,
  type Plan,
} from "@/lib/api";
import { ApiError } from "@/lib/api-types";

type TileProps = {
  slug: string;
  label: string;
  price: string;
  blurb: string;
  quota: string;
  isCurrent: boolean;
  ctaDisabled: boolean;
  disabledReason: string | null;
  onUpgrade?: () => void;
  busy: boolean;
};

const TILES: Array<Omit<TileProps, "isCurrent" | "ctaDisabled" | "disabledReason" | "onUpgrade" | "busy">> = [
  { slug: "free", label: "Free", price: "₾0", blurb: "Evaluate Angar.ai.", quota: "50 documents / month" },
  { slug: "pro", label: "Pro", price: "₾49 / month", blurb: "One-person practice.", quota: "100 documents / month" },
  { slug: "business", label: "Business", price: "₾249 / month", blurb: "Small accounting firm.", quota: "500 documents / month" },
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
  const disabledReason = ctaDisabled
    ? "Verify your email to enable billing."
    : null;

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
      <div className="grid grid-cols-3 gap-4">
        {TILES.map((tile) => {
          const isCurrent = tile.slug === currentPlan;
          return (
            <PlanTile
              key={tile.slug}
              {...tile}
              isCurrent={isCurrent}
              ctaDisabled={ctaDisabled || isCurrent || tile.slug === "free"}
              disabledReason={isCurrent ? "Current plan" : tile.slug === "free" ? null : disabledReason}
              onUpgrade={tile.slug === "free" ? undefined : () => upgrade(tile.slug as Plan)}
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
  label,
  price,
  blurb,
  quota,
  isCurrent,
  ctaDisabled,
  disabledReason,
  onUpgrade,
  busy,
}: TileProps) {
  return (
    <div
      className={
        "bg-paper border rounded-xl p-6 flex flex-col gap-3 " +
        (isCurrent ? "border-accent shadow-[0_0_0_3px_var(--color-accent-soft)]" : "border-line")
      }
    >
      <div className="flex items-baseline justify-between">
        <h3 className="font-serif text-[20px] m-0 tracking-[-0.015em] font-normal">{label}</h3>
        {isCurrent && (
          <span className="font-mono text-[10px] text-accent tracking-[0.06em] uppercase">
            Current
          </span>
        )}
      </div>
      <div className="font-serif text-[26px] tracking-[-0.02em] text-ink">{price}</div>
      <div className="text-[13px] text-ink-3 leading-relaxed">{blurb}</div>
      <div className="font-mono text-[11px] text-ink-3 tracking-[0.04em]">{quota}</div>
      <div className="mt-2">
        {onUpgrade ? (
          <Button
            variant={isCurrent ? "secondary" : "primary"}
            type="button"
            onClick={onUpgrade}
            disabled={ctaDisabled || busy}
            className="w-full justify-center"
          >
            {busy ? "Opening…" : isCurrent ? "Current plan" : `Upgrade to ${label}`}
          </Button>
        ) : (
          <span className="block text-center text-[12px] text-ink-3 italic">
            {isCurrent ? "Current plan" : "—"}
          </span>
        )}
      </div>
      {disabledReason && !isCurrent && (
        <p className="m-0 text-[11.5px] text-ink-3">{disabledReason}</p>
      )}
    </div>
  );
}
