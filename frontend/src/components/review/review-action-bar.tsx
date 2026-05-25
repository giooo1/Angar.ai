"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  approveExtraction,
  downloadExport,
  reextract,
  type ExportFormat,
} from "@/lib/api";

type Props = {
  documentId: string;
  extractionId: string;
  /** ISO timestamp if already approved, else null. */
  approvedAt: string | null;
  /** Base filename for downloads (extension added per format). */
  filenameBase: string;
};

const EXPORTS: { label: string; format: ExportFormat; color: string }[] = [
  { label: "XLSX · Excel", format: "xlsx", color: "#1d7044" },
  { label: "CSV", format: "csv", color: "var(--color-ink-2)" },
  { label: "JSON", format: "json", color: "#7a4eb8" },
];

/**
 * Sticky action bar at the foot of the right pane. Re-extract on the left
 * (ghost link); Export menu (CSV/XLSX/JSON) + Approve on the right.
 *
 * Approve marks the extraction reviewed (POST /approve, idempotent). Export
 * streams the file from the backend so encoding/serialization stay in one
 * place (UTF-8 BOM for CSV, openpyxl for XLSX).
 */
export function ReviewActionBar({ documentId, extractionId, approvedAt, filenameBase }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState<string | null>(approvedAt);
  const [err, setErr] = useState<string | null>(null);

  const onReextract = async () => {
    setBusy(true);
    try {
      const r = await reextract(documentId);
      router.push(`/review/${r.extraction_id}`);
    } catch {
      // Stay; user can retry. Toast system is later work.
    } finally {
      setBusy(false);
    }
  };

  const onApprove = async () => {
    setApproving(true);
    setErr(null);
    try {
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
      await downloadExport(extractionId, format, filenameBase);
    } catch {
      setErr(`Couldn't export ${format.toUpperCase()} — try again.`);
    }
  };

  return (
    <div className="sticky bottom-0 mt-1.5 flex items-center justify-between gap-3.5 py-5 pb-3 [background:linear-gradient(to_top,var(--color-bg)_80%,transparent)] backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onReextract}
          disabled={busy}
          className="text-[13px] text-ink-3 hover:text-ink-2 hover:underline font-[450] tracking-[-0.005em] cursor-pointer inline-flex items-center gap-1.5 disabled:opacity-50"
        >
          <span aria-hidden="true">↻</span>
          {busy ? "Re-extracting…" : "Re-extract"}
        </button>
        {err && <span className="text-[12.5px] text-[#b8342f]">{err}</span>}
      </div>
      <div className="flex gap-2.5 items-center">
        <div className="relative">
          <button
            type="button"
            onClick={() => setExportOpen((v) => !v)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-md bg-paper border border-line text-ink text-[13.5px] font-medium hover:border-ink-3 cursor-pointer"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            >
              <path d="M12 4v12m0 0l-4-4m4 4l4-4M4 20h16" />
            </svg>
            Export
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {exportOpen && (
            <div className="absolute bottom-[calc(100%+6px)] right-0 bg-paper border border-line rounded-lg min-w-[200px] p-1.5 shadow-[0_20px_40px_-16px_rgba(20,15,5,0.18)] z-10">
              {EXPORTS.map((opt) => (
                <button
                  key={opt.format}
                  type="button"
                  onClick={() => onExport(opt.format)}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-ink-2 hover:bg-bg cursor-pointer text-left"
                >
                  <span
                    className="doc-thumb"
                    style={{ width: 18, height: 22, color: opt.color }}
                  />
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
          className={
            approved
              ? "inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-[#1d7044] text-white text-[14px] font-medium hover:bg-[#185c38] cursor-pointer disabled:opacity-60"
              : "inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-ink text-bg text-[14px] font-medium hover:bg-[#2a3140] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          }
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 6L9 17l-5-5" />
          </svg>
          {approving ? "Approving…" : approved ? "Approved" : "Approve"}
        </button>
      </div>
    </div>
  );
}
