"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api-types";
import { changePassword, updateProfile } from "@/lib/api";
import type { UserDTO } from "@/lib/api-types";

type Props = { user: UserDTO };

/**
 * The Profile section of Settings. Full name + interface language persist via
 * PATCH /me; password changes in-place via POST /auth/change-password. Email
 * change and Default doc type are shown as "soon" (no backend yet).
 */
export function ProfileForm({ user }: Props) {
  const router = useRouter();

  const [name, setName] = useState(user.full_name ?? "");
  const [locale, setLocale] = useState(user.locale);
  const [savingName, setSavingName] = useState(false);
  const [nameMsg, setNameMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const nameDirty = name.trim() !== (user.full_name ?? "");

  const saveName = async () => {
    setSavingName(true);
    setNameMsg(null);
    try {
      await updateProfile({ full_name: name.trim() });
      setNameMsg({ ok: true, text: "Saved" });
      router.refresh();
    } catch {
      setNameMsg({ ok: false, text: "Couldn't save" });
    } finally {
      setSavingName(false);
    }
  };

  const setLanguage = async (next: string) => {
    if (next === locale) return;
    const prev = locale;
    setLocale(next);
    try {
      await updateProfile({ locale: next });
      router.refresh();
    } catch {
      setLocale(prev); // revert on failure
    }
  };

  return (
    <div className="bg-paper border border-line rounded-xl px-7 py-6">
      <h2 className="font-serif text-[20px] font-medium tracking-[-0.02em] m-0 mb-1">Profile</h2>
      <p className="text-[13.5px] text-ink-3 m-0 mb-3">Your account&apos;s basic information.</p>

      <Row
        label="Full name"
        action={
          <div className="flex items-center gap-2">
            {nameMsg && (
              <span className={cn("text-[12.5px]", nameMsg.ok ? "text-accent" : "text-error")}>
                {nameMsg.text}
              </span>
            )}
            <button
              type="button"
              onClick={saveName}
              disabled={savingName || !nameDirty}
              className="px-3.5 py-2 rounded-md bg-ink text-bg text-[13px] font-medium hover:bg-[#2a3140] cursor-pointer disabled:opacity-50 disabled:cursor-default"
            >
              {savingName ? "Saving…" : "Save"}
            </button>
          </div>
        }
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full max-w-[420px] px-3 py-2 border border-line rounded-md text-[13.5px] text-ink bg-paper outline-none focus:border-ink"
        />
      </Row>

      <Row
        label="Email"
        hint="used to sign in & receive notifications"
        action={
          <button
            type="button"
            disabled
            title="Coming soon"
            className="px-3.5 py-2 rounded-md text-[13px] text-ink-4 cursor-not-allowed"
          >
            Change
          </button>
        }
      >
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-[13px] text-ink">{user.email}</span>
          {user.email_verified_at ? (
            <span className="font-mono text-[10.5px] text-accent">✓ verified</span>
          ) : (
            <span className="font-mono text-[10.5px] text-warn">unverified</span>
          )}
        </div>
      </Row>

      <PasswordRow />

      <Row label="Language" hint="interface language (translation coming soon)">
        <Segmented
          options={[
            { value: "ka", label: "ქართული" },
            { value: "en", label: "English" },
          ]}
          value={locale}
          onChange={setLanguage}
        />
      </Row>

      <Row
        label="Default doc type"
        hint="picked automatically when type can be detected"
        last
      >
        <div title="Coming soon" className="opacity-60">
          <Segmented
            disabled
            options={[
              { value: "auto", label: "Auto-detect" },
              { value: "invoice", label: "Invoice" },
              { value: "waybill", label: "Waybill" },
            ]}
            value="auto"
            onChange={() => {}}
          />
        </div>
      </Row>
    </div>
  );
}

function PasswordRow() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const submit = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await changePassword(current, next);
      setMsg({ ok: true, text: "Password changed" });
      setCurrent("");
      setNext("");
      setOpen(false);
    } catch (e) {
      setMsg({
        ok: false,
        text: e instanceof ApiError ? e.messageEn : "Couldn't change password",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Row
      label="Password"
      hint="change it without leaving this page"
      action={
        <div className="flex items-center gap-2">
          {msg && (
            <span className={cn("text-[12.5px]", msg.ok ? "text-accent" : "text-error")}>
              {msg.text}
            </span>
          )}
          {open ? (
            <>
              <button
                type="button"
                onClick={submit}
                disabled={busy || !current || !next}
                className="px-3.5 py-2 rounded-md bg-ink text-bg text-[13px] font-medium hover:bg-[#2a3140] cursor-pointer disabled:opacity-50"
              >
                {busy ? "Saving…" : "Update"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setMsg(null);
                }}
                className="px-2 py-2 text-[13px] text-ink-3 hover:text-ink cursor-pointer"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => {
                setOpen(true);
                setMsg(null);
              }}
              className="px-3.5 py-2 rounded-md bg-paper border border-line text-ink text-[13px] font-medium hover:border-ink-3 cursor-pointer"
            >
              Change
            </button>
          )}
        </div>
      }
    >
      {open ? (
        <div className="flex flex-col gap-2 max-w-[420px]">
          <input
            type="password"
            placeholder="Current password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className="px-3 py-2 border border-line rounded-md text-[13px] outline-none focus:border-ink"
          />
          <input
            type="password"
            placeholder="New password (min 8 chars)"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            className="px-3 py-2 border border-line rounded-md text-[13px] outline-none focus:border-ink"
          />
        </div>
      ) : (
        <span className="font-mono text-[13px] text-ink-3 tracking-[0.12em]">••••••••••</span>
      )}
    </Row>
  );
}

function Row({
  label,
  hint,
  children,
  action,
  last,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 sm:grid-cols-[190px_1fr_auto] gap-x-4 gap-y-2 items-center py-4",
        !last && "border-b border-line-2",
      )}
    >
      <div className="text-[13.5px] text-ink font-medium">
        {label}
        {hint && <span className="block text-[12px] text-ink-3 font-normal mt-0.5">{hint}</span>}
      </div>
      <div className="min-w-0">{children}</div>
      <div className="sm:justify-self-end">{action}</div>
    </div>
  );
}

function Segmented({
  options,
  value,
  onChange,
  disabled,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="inline-flex bg-paper-2 border border-line-2 rounded-md p-0.5 gap-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          disabled={disabled}
          onClick={() => onChange(o.value)}
          className={cn(
            "px-3.5 py-1.5 rounded text-[12.5px] font-medium transition-colors",
            disabled ? "cursor-not-allowed" : "cursor-pointer",
            value === o.value
              ? "bg-paper text-ink shadow-[0_0_0_1px_var(--color-line)]"
              : "text-ink-3 hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
