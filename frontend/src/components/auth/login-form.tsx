"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { login } from "@/lib/api";
import { ApiError } from "@/lib/api-types";
import { GoogleButton, OrDivider } from "./google-button";

type Props = {
  /** Where to land after a successful login. Defaults to /upload. */
  next?: string;
};

/**
 * Email + password form. On success, hard-navigates so the middleware
 * sees the new session cookie on the next request.
 */
export function LoginForm({ next = "/upload" }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-3.5">
      <GoogleButton />
      <OrDivider />
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await login({ email, password });
            window.location.href = next;
          } catch (err) {
            setError(
              err instanceof ApiError
                ? err.messageEn
                : "Could not log in. Try again.",
            );
            setBusy(false);
          }
        }}
        className="flex flex-col gap-3.5"
      >
      <Field label="Email">
        <input
          type="email"
          required
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="auth-input"
        />
      </Field>
      <Field label="Password">
        <input
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="auth-input"
        />
      </Field>

      {error && <ErrorBanner message={error} />}

      <Button
        type="submit"
        variant="primary"
        disabled={busy}
        className="w-full justify-center mt-1.5"
      >
        {busy ? "Signing in…" : "Sign in"}
      </Button>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      {children}
    </label>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="bg-error-soft border border-[rgba(184,52,47,0.25)] text-[#7a201d] rounded-md px-3 py-2 text-[12.5px]">
      {message}
    </div>
  );
}
