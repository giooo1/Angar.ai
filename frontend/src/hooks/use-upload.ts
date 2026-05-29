"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, type ExtractionStatusResponse } from "@/lib/api-types";
import { pollExtraction, uploadDocument } from "@/lib/api";

/**
 * Per-file state machine. The Upload screen renders entries differently
 * by phase:
 *   queued / uploading / extracting -> "Processing" queue
 *   completed / failed              -> "Recent uploads" list
 */
export type UploadState =
  | { id: string; phase: "queued"; file: File; startedAt: number }
  | { id: string; phase: "uploading"; file: File; startedAt: number }
  | {
      id: string;
      phase: "extracting";
      file: File;
      documentId: string;
      extractionId: string;
      startedAt: number;
    }
  | {
      id: string;
      phase: "completed";
      file: File;
      documentId: string;
      extractionId: string;
      result: ExtractionStatusResponse;
      startedAt: number;
      durationMs: number;
    }
  | {
      id: string;
      phase: "failed";
      file: File;
      error: string;
      code?: string;
      documentId?: string;
      extractionId?: string;
      startedAt: number;
      durationMs?: number;
    };

let nextLocalId = 1;

/**
 * Manages the upload + poll lifecycle for one or more files.
 *
 * `addFiles(files)` kicks off the upload for each file in parallel.
 * `uploads` is the ordered list (newest first) of every file the user
 * has touched in this session — both in-flight and terminal.
 *
 * Lives in-memory only; reloading the page clears the list. Persistence
 * is a step-7 (Dashboard) concern.
 */
export function useUpload() {
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const abortRef = useRef<Map<string, AbortController>>(new Map());

  // Tear down any in-flight requests when the hook unmounts.
  useEffect(() => {
    const controllers = abortRef.current;
    return () => {
      for (const ctrl of controllers.values()) ctrl.abort();
      controllers.clear();
    };
  }, []);

  const patch = useCallback((id: string, next: Partial<UploadState>) => {
    setUploads((prev) =>
      prev.map((u) => (u.id === id ? ({ ...u, ...next } as UploadState) : u)),
    );
  }, []);

  const runOne = useCallback(
    async (state: UploadState) => {
      const ctrl = new AbortController();
      abortRef.current.set(state.id, ctrl);

      try {
        patch(state.id, { phase: "uploading" });
        const upload = await uploadDocument(state.file, ctrl.signal);
        patch(state.id, {
          phase: "extracting",
          documentId: upload.document_id,
          extractionId: upload.extraction_id,
        });

        // The sync backend already returns status="completed" on the
        // upload response, but we poll anyway so the code shape is
        // correct for when Celery lands.
        const final = await pollExtraction(
          upload.extraction_id,
          () => {
            // The phase already reflects "extracting"; we could surface
            // sub-states here if the backend later distinguishes
            // pending vs running. For now, just wait for terminal.
          },
          ctrl.signal,
        );

        if (final.status === "completed") {
          patch(state.id, {
            phase: "completed",
            documentId: upload.document_id,
            extractionId: upload.extraction_id,
            result: final,
            durationMs: Date.now() - state.startedAt,
          });
        } else {
          patch(state.id, {
            phase: "failed",
            documentId: upload.document_id,
            extractionId: upload.extraction_id,
            error: final.error_message ?? "extraction failed",
            durationMs: Date.now() - state.startedAt,
          });
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof ApiError) {
          patch(state.id, {
            phase: "failed",
            error: err.messageEn,
            code: err.code,
            durationMs: Date.now() - state.startedAt,
          });
        } else {
          patch(state.id, {
            phase: "failed",
            error: err instanceof Error ? err.message : String(err),
            durationMs: Date.now() - state.startedAt,
          });
        }
      } finally {
        abortRef.current.delete(state.id);
      }
    },
    [patch],
  );

  const addFiles = useCallback(
    (files: File[]) => {
      const fresh: UploadState[] = files.map((file) => ({
        id: `local-${nextLocalId++}`,
        phase: "queued" as const,
        file,
        startedAt: Date.now(),
      }));
      // Newest first, in front of older entries.
      setUploads((prev) => [...fresh, ...prev]);
      for (const f of fresh) void runOne(f);
    },
    [runOne],
  );

  const clear = useCallback(() => {
    for (const ctrl of abortRef.current.values()) ctrl.abort();
    abortRef.current.clear();
    setUploads([]);
  }, []);

  return { uploads, addFiles, clear };
}
