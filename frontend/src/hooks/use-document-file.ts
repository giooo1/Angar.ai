"use client";

import { useEffect, useState } from "react";

import { documentFileUrl } from "@/lib/api";

type DocumentFileState = {
  /** Object URL for the fetched bytes (PDF or image), or null while loading. */
  blobUrl: string | null;
  /** True when the upload is an image (jpg/png/heic…) rather than a PDF. */
  isImage: boolean;
  loading: boolean;
  error: string | null;
};

/**
 * Fetch a document's bytes from the backend with the session cookie and expose
 * them as an object URL. We fetch ourselves (rather than letting react-pdf do a
 * credentialed cross-origin request) and hand react-pdf a same-origin blob URL —
 * this avoids CORS-with-credentials edge cases and the detached-ArrayBuffer trap,
 * and lets us branch to an <img> for non-PDF uploads via the blob's MIME type.
 */
export function useDocumentFile(documentId: string): DocumentFileState {
  const [state, setState] = useState<DocumentFileState>({
    blobUrl: null,
    isImage: false,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    setState({ blobUrl: null, isImage: false, loading: true, error: null });

    (async () => {
      try {
        const res = await fetch(documentFileUrl(documentId), {
          credentials: "include",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setState({
          blobUrl: objectUrl,
          isImage: blob.type.startsWith("image/"),
          loading: false,
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        setState({
          blobUrl: null,
          isImage: false,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to load document",
        });
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId]);

  return state;
}
