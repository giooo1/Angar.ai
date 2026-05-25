"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { saveCorrections } from "@/lib/api";
import type { ExtractionStatusResponse } from "@/lib/api-types";
import type { CanonicalInvoice } from "@/lib/canonical";
import { countByBucket, meanConfidence } from "@/lib/confidence";

import { DataPane } from "./data-pane";
import { ExtractionErrorCard } from "./extraction-error-card";
import {
  ReviewEditProvider,
  setByPath,
  type ReviewEditContextValue,
} from "./review-edit-context";

// pdfjs is DOM-only; load the viewer client-side only.
const PdfViewer = dynamic(
  () => import("./pdf-viewer").then((m) => m.PdfViewer),
  {
    ssr: false,
    loading: () => (
      <div className="bg-paper-2 border border-line rounded-xl min-h-[480px] grid place-items-center text-[12.5px] text-ink-3 font-mono">
        Loading viewer…
      </div>
    ),
  },
);

type Props = {
  data: ExtractionStatusResponse;
};

type Tab = "document" | "data";

/**
 * Review screen shell: owns the edit draft + provider and the document-first
 * responsive layout.
 *
 * - ≥1280px: 60/40 (document/data). 768–1279px: 55/45. <768px: stacked with a
 *   Document | Data tab toggle (document first).
 * - The draft lives here so it can be shared with the fullscreen drawer (WS3);
 *   fields commit on blur via the edit context and read initial values from the
 *   draft, so a freshly-mounted pane always reflects prior edits.
 */
export function ReviewWorkspace({ data }: Props) {
  // Reviewer corrections win over the model's raw output.
  const canonical: CanonicalInvoice | null = data.corrected_data ?? data.canonical_data;

  const confidence = data.field_confidence ?? {};
  const overall = meanConfidence(confidence);
  const buckets = countByBucket(confidence);

  const draftRef = useRef<CanonicalInvoice | null>(null);
  if (draftRef.current === null && canonical) {
    draftRef.current = structuredClone(canonical);
  }
  const [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState<Tab>("document");

  const onSave = useCallback(async () => {
    if (draftRef.current) {
      await saveCorrections(data.extraction_id, draftRef.current);
      setDirty(false);
    }
  }, [data.extraction_id]);

  const ctx = useMemo<ReviewEditContextValue>(
    () => ({
      editable: true,
      updateField: (path, value) => {
        if (draftRef.current) {
          setByPath(draftRef.current as unknown as Record<string, unknown>, path, value);
          setDirty(true);
        }
      },
      updateItem: (index, key, value) => {
        const item = draftRef.current?.items?.[index];
        if (item) {
          setByPath(item as unknown as Record<string, unknown>, key, value);
          setDirty(true);
        }
      },
    }),
    [],
  );

  const filename = canonical?.extraction.source_filename ?? "document";

  return (
    <ReviewEditProvider value={ctx}>
      {/* Mobile tab toggle (hidden ≥768px) */}
      <div className="md:hidden mb-3 inline-flex rounded-lg border border-line bg-paper p-0.5 text-[13px] font-medium">
        {(["document", "data"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-1.5 rounded-md capitalize cursor-pointer transition-colors",
              tab === t ? "bg-ink text-bg" : "text-ink-3 hover:text-ink",
            )}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[55fr_45fr] xl:grid-cols-[60fr_40fr] gap-4 items-start">
        <div className={cn("min-w-0", tab !== "document" && "hidden md:block")}>
          <PdfViewer documentId={data.document_id} filename={filename} />
        </div>
        <div className={cn("min-w-0", tab !== "data" && "hidden md:block")}>
          {canonical ? (
            <DataPane
              data={data}
              canonical={draftRef.current ?? canonical}
              confidence={confidence}
              overall={overall}
              buckets={buckets}
              dirty={dirty}
              onSave={onSave}
            />
          ) : (
            <ExtractionErrorCard
              errorCode={data.error_code}
              errorMessage={data.error_message}
            />
          )}
        </div>
      </div>
    </ReviewEditProvider>
  );
}
