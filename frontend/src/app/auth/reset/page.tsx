"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { resetPassword } from "@/lib/api";
import { ApiError } from "@/lib/api-types";

/**
 * Token-gated password-reset form. On success the backend returns a
 * fresh session cookie + body; we hard-navigate to /upload so the
 * proxy + (app) layout pick up the new session.
 */
export default function ResetPage() {
  const params = useSearchParams();
  const token = params?.get("token") ?? null;
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token === null) {
    return (
      <AuthCard
        title="Reset"
        titleAccent="password"
        subtitle="This link is missing a token."
        footer={
          <Link href="/auth/request-reset" className="text-accent font-medium no-underline hover:underline">
            Request a new link
          </Link>
        }
      >
        <p className="text-[14px] text-ink-3 m-0">
          Reset links arrive by email. If you didn't get one, request another
          from the link below.
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Reset"
      titleAccent="password"
      subtitle="Choose a new password — at least 8 characters, one letter, one digit."
      footer={
        <Link href="/login" className="text-accent font-medium no-underline hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await resetPassword(token, password);
            window.location.href = "/upload";
          } catch (err) {
            setError(
              err instanceof ApiError
                ? err.messageEn
                : "Could not reset the password. Try requesting a new link.",
            );
            setBusy(false);
          }
        }}
        className="flex flex-col gap-3.5"
      >
        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
            New password
          </span>
          <input
            type="password"
            required
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
          {busy ? "Resetting…" : "Set new password"}
        </Button>
      </form>
    </AuthCard>
  );
}
