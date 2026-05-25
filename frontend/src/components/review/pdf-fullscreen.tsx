"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";
import type { ExtractionStatusResponse } from "@/lib/api-types";
import type { CanonicalInvoice } from "@/lib/canonical";

import { DataPane } from "./data-pane";
import { PdfViewer } from "./pdf-viewer";

type Props = {
  documentId: string;
  filename: string;
  onClose: () => void;
  // DataPane props (shared edit draft via the surrounding ReviewEditProvider)
  data: ExtractionStatusResponse;
  canonical: CanonicalInvoice;
  confidence: Record<string, number>;
  overall: number | null;
  dirty: boolean;
  onSave: () => Promise<void>;
};

/**
 * Fullscreen document overlay (portaled to <body>). The PDF fills the viewport
 * with the same minimal control bar; a drawer (open by default, collapsible)
 * holds the full, editable data pane on the right. Because this renders inside
 * the workspace's ReviewEditProvider, the drawer edits the same draft — a fix
 * made while zoomed persists and flows into Save/Export. Esc closes.
 */
export function PdfFullscreen({
  documentId,
  filename,
  onClose,
  data,
  canonical,
  confidence,
  overall,
  dirty,
  onSave,
}: Props) {
  const [drawerOpen, setDrawerOpen] = useState(true);

  // Esc to close + lock background scroll while open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  return createPortal(
    <div className="fixed inset-0 z-[100] flex bg-bg">
      <div className="flex-1 min-w-0">
        <PdfViewer
          documentId={documentId}
          filename={filename}
          fullscreen
          active
          onToggleFullscreen={onClose}
        />
      </div>

      <div
        className={cn(
          "relative h-full border-l border-line bg-bg transition-[width] duration-200 ease-out",
          drawerOpen ? "w-[min(460px,92vw)]" : "w-0",
        )}
      >
        <button
          type="button"
          onClick={() => setDrawerOpen((v) => !v)}
          title={drawerOpen ? "Hide data" : "Show data"}
          className="absolute top-1/2 -left-9 -translate-y-1/2 w-9 h-24 rounded-l-lg bg-paper border border-r-0 border-line text-ink-2 hover:text-ink grid place-items-center cursor-pointer shadow-[0_8px_24px_-16px_rgba(20,15,5,0.3)]"
        >
          <span className="[writing-mode:vertical-rl] rotate-180 font-mono text-[10.5px] tracking-[0.12em] uppercase">
            {drawerOpen ? "Hide" : "Data"}
          </span>
        </button>
        {drawerOpen && (
          <div className="h-full overflow-auto px-4 py-4">
            <DataPane
              data={data}
              canonical={canonical}
              confidence={confidence}
              overall={overall}
              dirty={dirty}
              onSave={onSave}
            />
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
