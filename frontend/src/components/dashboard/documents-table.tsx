"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { PlusIcon } from "@/components/ui/icons";
import { bulkDeleteExtractions, downloadBulkCsv } from "@/lib/api";
import type { ExtractionStatusResponse } from "@/lib/api-types";
import { DocumentRow } from "./document-row";

type Props = {
  items: ExtractionStatusResponse[];
};

const HEADER_GRID =
  "grid grid-cols-[28px_40px_1fr_120px_120px_200px_130px_110px_auto] gap-3 items-center px-4 py-3";

export function DocumentsTable({ items }: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className="bg-paper border border-line rounded-xl p-12 text-center">
        <p className="font-serif text-[20px] font-medium text-ink m-0 mb-2">
          No documents yet
        </p>
        <p className="text-[13px] text-ink-3 m-0 mb-5">
          Upload your first invoice to start building your library.
        </p>
        <Link href="/upload">
          <Button variant="accent">
            <PlusIcon size={14} strokeWidth={2} />
            Upload a document
          </Button>
        </Link>
      </div>
    );
  }

  const allSelected = items.every((i) => selected.has(i.extraction_id));
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(items.map((i) => i.extraction_id)));
  const clear = () => {
    setSelected(new Set());
    setConfirming(false);
    setErr(null);
  };

  const ids = [...selected];

  const onExport = async () => {
    setBusy(true);
    setErr(null);
    try {
      await downloadBulkCsv(ids);
    } catch {
      setErr("Couldn't export — try again.");
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async () => {
    setBusy(true);
    setErr(null);
    try {
      await bulkDeleteExtractions(ids);
      clear();
      router.refresh(); // re-fetch list + nav badge
    } catch {
      setErr("Couldn't delete — try again.");
      setBusy(false);
    }
  };

  return (
    <div className="bg-paper border border-line rounded-xl overflow-hidden">
      {selected.size > 0 ? (
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-line-2 bg-accent-soft/60">
          <span className="text-[13px] font-medium text-ink">{selected.size} selected</span>
          {err && <span className="text-[12.5px] text-[#b8342f]">{err}</span>}
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={onExport}
              disabled={busy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-paper border border-line text-ink text-[13px] font-medium hover:border-ink-3 cursor-pointer disabled:opacity-60"
            >
              Export CSV
            </button>
            {confirming ? (
              <>
                <span className="text-[12.5px] text-ink-2">Delete {selected.size}?</span>
                <button
                  type="button"
                  onClick={onDelete}
                  disabled={busy}
                  className="px-3 py-1.5 rounded-md bg-error text-white text-[13px] font-medium hover:brightness-95 cursor-pointer disabled:opacity-60"
                >
                  {busy ? "Deleting…" : "Confirm"}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  className="px-2 py-1.5 text-[13px] text-ink-3 hover:text-ink cursor-pointer"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setConfirming(true)}
                className="px-3 py-1.5 rounded-md border border-error/40 text-error text-[13px] font-medium hover:bg-error-soft cursor-pointer"
              >
                Delete
              </button>
            )}
            <button
              type="button"
              onClick={clear}
              className="px-2 py-1.5 text-[13px] text-ink-3 hover:text-ink cursor-pointer"
            >
              Clear
            </button>
          </div>
        </div>
      ) : (
        <div
          className={`${HEADER_GRID} border-b border-line-2 bg-paper-2 font-mono text-[10.5px] text-ink-3 tracking-[0.06em] uppercase`}
        >
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            aria-label="Select all"
            className="w-3.5 h-3.5 cursor-pointer accent-[var(--color-accent-2)]"
          />
          <span />
          <span>Document</span>
          <span>Type</span>
          <span>Date</span>
          <span>Seller</span>
          <span>Grand total</span>
          <span>Status</span>
          <span className="text-right">Action</span>
        </div>
      )}
      {items.map((item) => (
        <DocumentRow
          key={item.extraction_id}
          item={item}
          selected={selected.has(item.extraction_id)}
          onToggle={() => toggle(item.extraction_id)}
        />
      ))}
    </div>
  );
}
