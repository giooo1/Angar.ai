"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getExtraction, pollExtraction } from "@/lib/api";
import {
  ApiError,
  type ExtractionStatusResponse,
} from "@/lib/api-types";

type State =
  | { phase: "loading"; data: null; error: null }
  | { phase: "polling"; data: ExtractionStatusResponse; error: null }
  | { phase: "ready"; data: ExtractionStatusResponse; error: null }
  | { phase: "error"; data: null; error: string };

/**
 * Fetch + poll one extraction by id.
 *
 * Initial fetch on mount. If the extraction comes back with a terminal
 * status (completed/failed) we stop — the sync backend currently always
 * does. If the status is pending/running, we poll until terminal.
 *
 * `reload()` re-runs the same flow (used by the re-extract button after
 * it kicks off a new extraction).
 */
export function useExtraction(extractionId: string | null) {
  const [state, setState] = useState<State>({
    phase: "loading",
    data: null,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async () => {
    if (!extractionId) {
      setState({ phase: "error", data: null, error: "missing extraction id" });
      return;
    }
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ phase: "loading", data: null, error: null });

    try {
      const first = await getExtraction(extractionId, ctrl.signal);
      if (first.status === "completed" || first.status === "failed") {
        setState({ phase: "ready", data: first, error: null });
        return;
      }

      setState({ phase: "polling", data: first, error: null });
      const terminal = await pollExtraction(
        extractionId,
        (snapshot) => {
          setState({ phase: "polling", data: snapshot, error: null });
        },
        ctrl.signal,
      );
      setState({ phase: "ready", data: terminal, error: null });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const message =
        err instanceof ApiError
          ? err.messageEn
          : err instanceof Error
            ? err.message
            : String(err);
      setState({ phase: "error", data: null, error: message });
    }
  }, [extractionId]);

  useEffect(() => {
    void run();
    return () => abortRef.current?.abort();
  }, [run]);

  const isLoading = state.phase === "loading" || state.phase === "polling";

  return {
    data: state.data,
    error: state.error,
    isLoading,
    phase: state.phase,
    reload: run,
  };
}
