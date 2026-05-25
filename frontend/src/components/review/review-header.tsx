"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { cn } from "@/lib/utils";
import {
  approveExtraction,
  downloadExport,
  reextract,
  type ExportFormat,
} from "@/lib/api";

type Props = {
  documentId: string;
  extractionId: string;
  approvedAt: string | null;
  filenameBase: string;
  dirty: boolean;
  onSave: () => Promise<void>;
  accepted: boolean;
  /** Mean field confidence in [0,1], or null when no scores. */
  overall: number | null;
};

const EXPORTS: { label: string; format: ExportFormat; color: string }[] = [
  { label: "XLSX · Excel", format: "xlsx", color: "#1d7044" },
  { label: "CSV", format: "csv", color: "var(--color-ink-2)" },
  { label: "JSON", format: "json", color: "#7a4eb8" },
];

/**
 * Sticky header at the top of the data pane. Carries the accepted state +
 * overall confidence on the left and the primary actions (Save · Export ·
 * Approve) on the right, so they stay visible while scrolling a long
 * extraction. Replaces both the old top acceptance banner and the bottom
 * action bar.
 *
 * Save persists reviewer edits (PUT /corrections). Approve and Export flush
 * unsaved edits first, so a sign-off or download always reflects the screen.
 */
export function ReviewHeader({
  documentId,
  extractionId,
  approvedAt,
  filenameBase,
  dirty,
  onSave,
  accepted,
  overall,
}: Props) {
  const router = useRouter();
  const [exportOpen, setExportOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState<string | null>(approvedAt);
  const [err, setErr] = useState<string | null>(null);

  const onSaveClick = async () => {
    setSaving(true);
    setErr(null);
    try {
      await onSave();
    } catch {
      setErr("Couldn't save — try again.");
    } finally {
      setSaving(false);
    }
  };

  const onApprove = async () => {
    setApproving(true);
    setErr(null);
    try {
      if (dirty) await onSave();
      const r = await approveExtraction(extractionId);
      setApproved(r.approved_at);
    } catch {
      setErr("Couldn't approve — try again.");
    } finally {
      setApproving(false);
    }
  };

  const onExport = async (format: ExportFormat) => {
    setExportOpen(false);
    setErr(null);
    try {
      if (dirty) await onSave();
      await downloadExport(extractionId, format, filenameBase);
    } catch {
      setErr(`Couldn't export ${format.toUpperCase()} — try again.`);
    }
  };

  const onReextract = async () => {
    setBusy(true);
    try {
      const r = await reextract(documentId);
      router.push(`/review/${r.extraction_id}`);
    } catch {
      // user can retry
    } finally {
      setBusy(false);
    }
  };

  return (
    <header className="sticky top-4 z-20 flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl border border-line bg-paper/95 backdrop-blur-sm shadow-[0_8px_24px_-18px_rgba(20,15,5,0.25)]">
      <div className="flex items-center gap-2.5 min-w-0">
        <span
          className={cn(
            "w-[26px] h-[26px] rounded-full bg-paper border-[1.5px] grid place-items-center flex-none font-bold text-[13px]",
            accepted ? "border-accent text-accent" : "border-error text-error",
          )}
        >
          {accepted ? "✓" : "!"}
        </span>
        <div className="min-w-0 leading-tight">
          <div className="font-serif text-[14px] font-medium tracking-[-0.01em] text-ink truncate">
            {accepted ? "Document accepted" : "Document rejected"}
          </div>
          <div className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em]">
            {overall !== null ? `${(overall * 100).toFixed(1)}% overall` : "—"}
            {err && <span className="text-[#b8342f] ml-2">· {err}</span>}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onReextract}
          disabled={busy}
          title="Re-extract"
          className="hidden sm:inline-flex text-[12.5px] text-ink-3 hover:text-ink-2 hover:underline font-[450] cursor-pointer items-center gap-1 disabled:opacity-50"
        >
          <span aria-hidden="true">↻</span>
          {busy ? "…" : "Re-extract"}
        </button>
        <button
          type="button"
          onClick={onSaveClick}
          disabled={!dirty || saving}
          title={dirty ? "Save your edits" : "No unsaved changes"}
          className="inline-flex items-center px-3 py-1.5 rounded-md text-[13px] font-medium cursor-pointer disabled:cursor-default enabled:bg-accent-soft enabled:text-accent enabled:hover:brightness-95 disabled:text-ink-3"
        >
          {saving ? "Saving…" : dirty ? "Save" : "Saved"}
        </button>
        <div className="relative">
          <button
            type="button"
            onClick={() => setExportOpen((v) => !v)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-paper border border-line text-ink text-[13px] font-medium hover:border-ink-3 cursor-pointer"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M12 4v12m0 0l-4-4m4 4l4-4M4 20h16" />
            </svg>
            Export
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {exportOpen && (
            <div className="absolute top-[calc(100%+6px)] right-0 bg-paper border border-line rounded-lg min-w-[190px] p-1.5 shadow-[0_20px_40px_-16px_rgba(20,15,5,0.18)] z-30">
              {EXPORTS.map((opt) => (
                <button
                  key={opt.format}
                  type="button"
                  onClick={() => onExport(opt.format)}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-ink-2 hover:bg-bg cursor-pointer text-left"
                >
                  <span className="doc-thumb" style={{ width: 16, height: 20, color: opt.color }} />
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onApprove}
          disabled={approving}
          className={cn(
            "inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md text-[13px] font-medium cursor-pointer disabled:opacity-60",
            approved
              ? "bg-[#1d7044] text-white hover:bg-[#185c38]"
              : "bg-ink text-bg hover:bg-[#2a3140]",
          )}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6L9 17l-5-5" />
          </svg>
          {approving ? "…" : approved ? "Approved" : "Approve"}
        </button>
      </div>
    </header>
  );
}
