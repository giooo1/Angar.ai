"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { reextract } from "@/lib/api";

type Props = {
  documentId: string;
};

/**
 * Sticky action bar at the foot of the right pane. Re-extract on the
 * left (ghost link), Export menu + Save on the right.
 *
 * Export and Save are intentional no-ops for v1 — they exist in the
 * design as affordances. Export lands when XLSX/CSV/JSON serializers
 * are wired; Save lands with the corrections table.
 */
export function ReviewActionBar({ documentId }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

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

  return (
    <div className="sticky bottom-0 mt-1.5 flex items-center justify-between gap-3.5 py-5 pb-3 [background:linear-gradient(to_top,var(--color-bg)_80%,transparent)] backdrop-blur-sm">
      <div>
        <button
          type="button"
          onClick={onReextract}
          disabled={busy}
          className="text-[13px] text-ink-3 hover:text-ink-2 hover:underline font-[450] tracking-[-0.005em] cursor-pointer inline-flex items-center gap-1.5 disabled:opacity-50"
        >
          <span aria-hidden="true">↻</span>
          {busy ? "Re-extracting…" : "Re-extract"}
        </button>
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
              {[
                { label: "XLSX · Excel", color: "#1d7044" },
                { label: "CSV", color: "var(--color-ink-2)" },
                { label: "JSON", color: "#7a4eb8" },
              ].map((opt) => (
                <button
                  key={opt.label}
                  type="button"
                  disabled
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-ink-3 opacity-70 cursor-not-allowed text-left"
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
          disabled
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-ink text-bg text-[14px] font-medium hover:bg-[#2a3140] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          Save
        </button>
      </div>
    </div>
  );
}
