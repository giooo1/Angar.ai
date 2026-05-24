"use client";

import { useState } from "react";

/**
 * Single-line banner shown above the topbar when the current user's
 * email is still unverified. Soft gate: the app keeps working, but
 * billing is blocked until the address is confirmed.
 *
 * The "Resend" link points back to /auth/request-reset for now — we
 * haven't built a dedicated resend-verification endpoint yet. (When
 * we do, this swaps to that path; one-line change.)
 */
export function VerificationBanner({ email }: { email: string }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div className="bg-warn-soft border-b border-[rgba(184,136,32,0.25)] text-[#5a4310] px-7 py-2 flex items-center justify-between gap-3 text-[12.5px]">
      <span>
        Verify your email (<span className="font-medium">{email}</span>) to
        enable billing. Check your inbox for the confirmation link.
      </span>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="text-ink-3 hover:text-ink text-[14px] leading-none px-1.5 py-0.5 cursor-pointer"
      >
        ×
      </button>
    </div>
  );
}
