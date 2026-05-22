"use client";

import Link from "next/link";
import type { UploadState } from "@/hooks/use-upload";
import { cn } from "@/lib/utils";

type Props = {
  /** Most-recent completed / failed uploads, newest first. */
  items: UploadState[];
};

/**
 * Right-column list of recent completed/failed uploads. Each row links to
 * /review/<extractionId> (placeholder until step 4 lands). Renders an
 * empty state when no uploads have completed yet.
 */
export function RecentUploads({ items }: Props) {
  return (
    <div className="bg-paper border border-line rounded-xl p-[18px]">
      <h3 className="m-0 mb-3 font-serif text-[17px] font-medium tracking-[-0.015em] flex items-center justify-between">
        Recent uploads
        <Link
          href="/dashboard"
          className="font-mono text-[11px] text-ink-3 tracking-[0.04em] font-normal normal-case no-underline hover:text-ink"
        >
          View all
        </Link>
      </h3>

      {items.length === 0 ? (
        <p className="m-0 py-6 text-center text-[13px] text-ink-3">
          No uploads yet. Drag a PDF or click the drop zone to start.
        </p>
      ) : (
        <ul className="m-0 p-0 list-none flex flex-col">
          {items.map((item, idx) => (
            <RecentItem key={item.id} item={item} last={idx === items.length - 1} />
          ))}
        </ul>
      )}
    </div>
  );
}

function RecentItem({ item, last }: { item: UploadState; last: boolean }) {
  if (item.phase !== "completed" && item.phase !== "failed") return null;

  const canonical =
    item.phase === "completed"
      ? (item.result.canonical_data as Record<string, unknown> | null)
      : null;
  const sellerName =
    canonical && typeof canonical.seller === "object" && canonical.seller
      ? (canonical.seller as { name?: string }).name
      : undefined;
  const docNumber =
    canonical && typeof canonical.document_number === "string"
      ? canonical.document_number
      : undefined;
  const docDate =
    canonical && typeof canonical.document_date === "string"
      ? canonical.document_date
      : undefined;

  const sub =
    item.phase === "failed"
      ? item.error
      : [sellerName, docNumber, docDate].filter(Boolean).join(" · ") ||
        "extracted";

  const href =
    item.phase === "completed" || item.extractionId
      ? `/review/${item.extractionId ?? ""}`
      : "/upload";

  return (
    <li
      className={cn(
        "grid grid-cols-[28px_1fr_auto] gap-3 items-center py-2.5",
        !last && "border-b border-line-2",
      )}
    >
      <span className="doc-thumb" />
      <Link
        href={href}
        className="min-w-0 no-underline group"
      >
        <div className="text-[13px] font-medium text-ink overflow-hidden text-ellipsis whitespace-nowrap group-hover:text-accent transition-colors">
          {item.file.name}
        </div>
        <div className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em] mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap">
          {sub}
        </div>
      </Link>
      <StatusPill phase={item.phase} />
    </li>
  );
}

function StatusPill({ phase }: { phase: "completed" | "failed" }) {
  const isOk = phase === "completed";
  return (
    <span
      className={cn(
        "font-mono text-[10.5px] tracking-[0.04em] inline-flex items-center gap-1.5",
        isOk ? "text-accent" : "text-error",
      )}
    >
      <span
        className={cn(
          "w-[5px] h-[5px] rounded-full",
          isOk ? "bg-accent-2" : "bg-error",
        )}
      />
      {isOk ? "done" : "failed"}
    </span>
  );
}
