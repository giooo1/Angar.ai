"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { register } from "@/lib/api";
import { ApiError } from "@/lib/api-types";

/**
 * Signup form: full name + email + password + organization name.
 * On success, hard-navigates so the middleware sees the new cookie.
 */
export function SignupForm() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await register({
            email,
            password,
            full_name: fullName || undefined,
            organization_name: orgName,
          });
          window.location.href = "/upload";
        } catch (err) {
          setError(
            err instanceof ApiError
              ? err.messageEn
              : "Could not create the account. Try again.",
          );
          setBusy(false);
        }
      }}
      className="flex flex-col gap-3.5"
    >
      <Field label="Full name (optional)">
        <input
          type="text"
          autoComplete="name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="auth-input"
        />
      </Field>
      <Field label="Organization name">
        <input
          type="text"
          required
          autoComplete="organization"
          value={orgName}
          onChange={(e) => setOrgName(e.target.value)}
          className="auth-input"
        />
      </Field>
      <Field label="Email">
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="auth-input"
        />
      </Field>
      <Field label="Password">
        <input
          type="password"
          required
          autoComplete="new-password"
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="auth-input"
        />
        <span className="text-[11px] text-ink-3 mt-0.5">
          At least 8 characters, with one letter and one digit.
        </span>
      </Field>

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
        {busy ? "Creating account…" : "Create account"}
      </Button>
    </form>
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
