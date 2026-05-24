"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { verifyEmail } from "@/lib/api";
import { ApiError } from "@/lib/api-types";

type State =
  | { kind: "pending" }
  | { kind: "success" }
  | { kind: "error"; message: string };

/**
 * Email-verification landing page. The `token` is the auth — no login
 * required. Reads `?token=` from the URL and POSTs to the backend.
 * On success offers a quick link back into the app.
 */
export default function VerifyEmailPage() {
  const params = useSearchParams();
  const token = params?.get("token") ?? null;
  const [state, setState] = useState<State>({ kind: "pending" });

  useEffect(() => {
    if (token === null) {
      setState({ kind: "error", message: "This link is missing the token." });
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        await verifyEmail(token);
        if (!cancelled) setState({ kind: "success" });
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof ApiError
            ? err.messageEn
            : "Could not verify the link. It may have expired.";
        setState({ kind: "error", message });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <AuthCard
      title="Email"
      titleAccent="verification"
      subtitle="Confirming your address with the backend…"
      footer={
        <Link href="/login" className="text-accent font-medium no-underline hover:underline">
          Back to sign in
        </Link>
      }
    >
      {state.kind === "pending" && (
        <p className="text-[14px] text-ink-3 m-0">
          One moment — checking the link.
        </p>
      )}
      {state.kind === "success" && (
        <div className="flex flex-col gap-4">
          <p className="text-[14px] text-ink m-0">
            Your email is verified. Billing is now enabled on your account.
          </p>
          <Link href="/upload">
            <Button variant="primary" className="w-full justify-center">
              Open the app
            </Button>
          </Link>
        </div>
      )}
      {state.kind === "error" && (
        <div className="bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-md px-3 py-2 text-[12.5px]">
          {state.message}
        </div>
      )}
    </AuthCard>
  );
}
