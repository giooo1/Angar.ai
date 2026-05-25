"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

const TYPES: [string, string][] = [
  ["", "All types"],
  ["vat_invoice", "VAT invoice"],
  ["regular_invoice", "Invoice"],
  ["waybill", "Waybill"],
  ["receipt", "Receipt"],
  ["utility_bill", "Utility bill"],
  ["payment_order", "Payment order"],
  ["unknown", "Unknown"],
];

const ACCEPTANCE: [string, string][] = [
  ["", "Any status"],
  ["true", "Accepted"],
  ["false", "Rejected"],
];

const control =
  "h-9 px-3 rounded-md border border-line bg-paper text-[13px] text-ink outline-none focus:border-ink-3 cursor-pointer";

/**
 * Search + filter bar for the Documents archive. State lives in the URL query
 * so the server component re-renders filtered; changing any filter resets to
 * page 1. The worklist deliberately has no equivalent — the queue is the filter.
 */
export function ArchiveFilters() {
  const router = useRouter();
  const sp = useSearchParams();

  const q = sp.get("q") ?? "";
  const type = sp.get("document_type") ?? "";
  const accepted = sp.get("accepted") ?? "";
  const hasCorrections = sp.get("has_corrections") === "true";
  const dateFrom = sp.get("date_from") ?? "";
  const dateTo = sp.get("date_to") ?? "";

  const anyActive = Boolean(q || type || accepted || hasCorrections || dateFrom || dateTo);

  const push = (mut: (p: URLSearchParams) => void) => {
    const p = new URLSearchParams(Array.from(sp.entries()));
    mut(p);
    p.delete("page"); // any filter change returns to the first page
    const qs = p.toString();
    router.push(qs ? `/dashboard?${qs}` : "/dashboard");
  };

  const setParam = (key: string, value: string) =>
    push((p) => (value ? p.set(key, value) : p.delete(key)));

  // Debounced search so each keystroke doesn't hit the server.
  const [search, setSearch] = useState(q);
  useEffect(() => setSearch(q), [q]); // stay in sync when cleared elsewhere
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const onSearch = (v: string) => {
    setSearch(v);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setParam("q", v.trim()), 300);
  };

  return (
    <div className="flex flex-wrap items-center gap-2 mb-5">
      <input
        value={search}
        onChange={(e) => onSearch(e.target.value)}
        placeholder="Search filename, seller, number…"
        className={cn(control, "w-[260px] cursor-text")}
      />
      <select
        value={type}
        onChange={(e) => setParam("document_type", e.target.value)}
        className={control}
        aria-label="Document type"
      >
        {TYPES.map(([v, label]) => (
          <option key={v} value={v}>
            {label}
          </option>
        ))}
      </select>
      <select
        value={accepted}
        onChange={(e) => setParam("accepted", e.target.value)}
        className={control}
        aria-label="Acceptance status"
      >
        {ACCEPTANCE.map(([v, label]) => (
          <option key={v} value={v}>
            {label}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() =>
          push((p) =>
            hasCorrections ? p.delete("has_corrections") : p.set("has_corrections", "true"),
          )
        }
        className={cn(
          "h-9 px-3 rounded-md border text-[13px] font-medium cursor-pointer transition-colors",
          hasCorrections
            ? "bg-accent-soft border-accent/30 text-accent"
            : "bg-paper border-line text-ink-2 hover:border-ink-3",
        )}
      >
        Edited only
      </button>
      <label className="inline-flex items-center gap-1.5 text-[12px] text-ink-3">
        From
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setParam("date_from", e.target.value)}
          className={control}
          aria-label="Invoice date from"
        />
      </label>
      <label className="inline-flex items-center gap-1.5 text-[12px] text-ink-3">
        To
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setParam("date_to", e.target.value)}
          className={control}
          aria-label="Invoice date to"
        />
      </label>
      {anyActive && (
        <button
          type="button"
          onClick={() => router.push("/dashboard")}
          className="h-9 px-3 text-[13px] text-ink-3 hover:text-ink hover:underline cursor-pointer"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
