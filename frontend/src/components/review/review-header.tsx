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
import { CheckIcon, DownloadIcon, RefreshCwIcon } from "@/components/ui/icons";

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
  /** Count of fields below 90%. */
  needsReview: number;
};

const EXPORTS: { label: string; format: ExportFormat; color: string }[] = [
  { label: "XLSX · Excel", format: "xlsx", color: "#1d7044" },
  { label: "CSV", format: "csv", color: "var(--color-ink-2)" },
  { label: "JSON", format: "json", color: "#7a4eb8" },
];

/**
 * Sticky header for the data pane. Left: accepted/rejected title + a one-line
 * confidence subtitle. Right: a tight action group — Re-extract (text),
 * Save + Export (outline), Approve (filled green). Approve and Export flush
 * unsaved edits first.
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
  needsReview,
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

  const subtitle = [
    overall !== null ? `${Math.round(overall * 100)}% overall confidence` : null,
    `${needsReview} ${needsReview === 1 ? "field needs" : "fields need"} review`,
  ]
    .filter(Boolean)
    .join(" · ");

  const outline =
    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-paper border border-line text-ink text-[13px] font-medium hover:border-ink-3 cursor-pointer disabled:cursor-default disabled:opacity-60";

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-3 py-2.5 mb-1 bg-paper/95 backdrop-blur-sm">
      <div className="min-w-0">
        <div
          className={cn(
            "text-[15px] font-medium tracking-[-0.01em] leading-tight",
            accepted ? "text-ink" : "text-error",
          )}
        >
          {accepted ? "Document accepted" : "Document rejected"}
        </div>
        <div className="text-[13px] text-ink-3 leading-tight mt-0.5">
          {subtitle}
          {err && <span className="text-error ml-2">· {err}</span>}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onReextract}
          disabled={busy}
          title="Re-extract"
          className="inline-flex items-center gap-1 text-[13px] text-ink-3 hover:text-ink-2 font-[450] cursor-pointer disabled:opacity-50"
        >
          <RefreshCwIcon size={13} />
          {busy ? "…" : "Re-extract"}
        </button>
        <button
          type="button"
          onClick={onSaveClick}
          disabled={!dirty || saving}
          title={dirty ? "Save your edits" : "No unsaved changes"}
          className={outline}
        >
          {saving ? "Saving…" : dirty ? "Save" : "Saved"}
        </button>
        <div className="relative">
          <button type="button" onClick={() => setExportOpen((v) => !v)} className={outline}>
            <DownloadIcon size={13} />
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
          className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-accent-2 text-white text-[13px] font-medium hover:brightness-95 cursor-pointer disabled:opacity-60"
        >
          <CheckIcon size={13} />
          {approving ? "…" : approved ? "Approved" : "Approve"}
        </button>
      </div>
    </header>
  );
}
