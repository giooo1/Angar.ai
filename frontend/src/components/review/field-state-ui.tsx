"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { formatPct, isVerified, setVerified, type FieldState } from "@/lib/confidence";

/**
 * Shared "user-confirmed" toggle backed by localStorage. Returns the current
 * confirmed flag and a setter that persists it. Used by every review block so
 * the verified affordance behaves identically across them.
 */
export function useConfirmed(
  extractionId: string,
  fieldPath: string,
): { confirmed: boolean; toggle: () => void } {
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    setConfirmed(isVerified(extractionId, fieldPath));
  }, [extractionId, fieldPath]);

  const toggle = () => {
    const next = !confirmed;
    setVerified(extractionId, fieldPath, next);
    setConfirmed(next);
  };

  return { confirmed, toggle };
}

/**
 * Right-hand state chip for the two-axis model. Clicking confirms (or un-
 * confirms) the field. `confirmed` distinguishes a user-checked field
 * ("Confirmed") from one the model read confidently ("Verified").
 */
export function StateChip({
  state,
  score,
  confirmed,
  onToggle,
  className,
}: {
  state: FieldState;
  score: number | undefined;
  confirmed: boolean;
  onToggle: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      title={confirmed ? "Click to unconfirm" : "Click to mark confirmed"}
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-md border font-mono font-semibold tracking-[0.02em] cursor-pointer transition-[filter] hover:brightness-95",
        state === "verified" &&
          "bg-paper text-accent border-accent/30 uppercase text-[9.5px] tracking-[0.05em]",
        state === "check" && "bg-warn-soft text-[#7a5a13] border-warn/30 text-[10.5px]",
        state === "empty" &&
          "bg-neutral-soft text-[#5d626c] border-neutral-line uppercase text-[9.5px] tracking-[0.05em]",
        className,
      )}
    >
      {state === "verified" && (
        <>
          <span className="font-bold text-accent-2">✓</span>
          <span>{confirmed ? "Confirmed" : "Verified"}</span>
        </>
      )}
      {state === "check" && <span>{formatPct(score)}</span>}
      {state === "empty" && (
        <>
          <span className="w-1.5 h-1.5 rounded-full bg-neutral" aria-hidden="true" />
          <span>Empty</span>
        </>
      )}
    </button>
  );
}
