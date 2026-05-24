"use client";

import Link from "next/link";
import { useState } from "react";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { requestPasswordReset } from "@/lib/api";
import { ApiError } from "@/lib/api-types";

/**
 * Email-only form. Backend returns 204 whether or not the email maps
 * to a real user, so the success copy is the same in both cases (no
 * account enumeration).
 */
export default function RequestResetPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <AuthCard
      title="Reset"
      titleAccent="password"
      subtitle="Enter your email and we'll send a reset link if that account exists."
      footer={
        <Link href="/login" className="text-accent font-medium no-underline hover:underline">
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <p className="text-[14px] text-ink m-0">
          If <span className="font-medium">{email}</span> belongs to an Angar.ai account, a reset link is on its way. The link expires in one hour.
        </p>
      ) : (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError(null);
            try {
              await requestPasswordReset(email);
              setSent(true);
            } catch (err) {
              setError(
                err instanceof ApiError
                  ? err.messageEn
                  : "Couldn't send the reset link. Try again.",
              );
            } finally {
              setBusy(false);
            }
          }}
          className="flex flex-col gap-3.5"
        >
          <label className="flex flex-col gap-1.5">
            <span className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
              Email
            </span>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="auth-input"
            />
          </label>

          {error && (
            <div className="bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-md px-3 py-2 text-[12.5px]">
              {error}
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            disabled={busy}
            className="w-full justify-center mt-1.5"
          >
            {busy ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
