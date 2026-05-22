"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { reextract } from "@/lib/api";

/**
 * Triggers a new extraction against the same Document and navigates to
 * the new extraction's review page. Disables itself during the in-flight
 * request to prevent double-clicks.
 *
 * The new extraction's status will be `completed` on landing (sync
 * backend) — the destination page's useExtraction hook handles the case
 * where it's still running by polling.
 */
export function ReextractButton({ documentId }: { documentId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  return (
    <Button
      variant="secondary"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          const result = await reextract(documentId);
          router.push(`/review/${result.extraction_id}`);
        } catch {
          // Errors fall through; the user can retry. A toast system
          // would land in a later step.
        } finally {
          setBusy(false);
        }
      }}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 4v6h6M20 20v-6h-6" />
        <path d="M20 10A8 8 0 005.6 5.6M4 14a8 8 0 0014.4 4.4" />
      </svg>
      {busy ? "Re-extracting…" : "Re-extract"}
    </Button>
  );
}
