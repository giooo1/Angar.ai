"use client";

import { createContext, useContext } from "react";

import { useUpload, type UploadState } from "@/hooks/use-upload";

type UploadContextValue = {
  uploads: UploadState[];
  addFiles: (files: File[]) => void;
  clear: () => void;
};

const UploadContext = createContext<UploadContextValue | null>(null);

/**
 * Holds the upload state above the route pages (mounted in the app layout),
 * so the Activity list — including in-flight uploads and the "Just processed"
 * entries — survives navigation between /upload, /documents, /settings.
 */
export function UploadProvider({ children }: { children: React.ReactNode }) {
  const value = useUpload();
  return <UploadContext.Provider value={value}>{children}</UploadContext.Provider>;
}

export function useUploadContext(): UploadContextValue {
  const ctx = useContext(UploadContext);
  if (!ctx) {
    throw new Error("useUploadContext must be used within <UploadProvider>");
  }
  return ctx;
}
