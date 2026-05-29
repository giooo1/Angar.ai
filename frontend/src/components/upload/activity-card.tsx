"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import type { UploadState } from "@/hooks/use-upload";
import { cn } from "@/lib/utils";

type Props = {
  items: UploadState[];
};

/**
 * Single right-column card on /upload showing every file from this
 * session. In-flight rows live under "Processing" with a shimmer rail
 * and live elapsed-time text; completed rows roll into "Just processed"
 * with a Review → button. Empty state shows a quiet placeholder.
 *
 * Replaces the previous UploadQueue + RecentUploads split.
 */
export function ActivityCard({ items }: Props) {
  const inFlight = items.filter(
    (u) => u.phase === "queued" || u.phase === "uploading" || u.phase === "extracting",
  );
  const done = items.filter((u) => u.phase === "completed" || u.phase === "failed");
  const activeCount = items.filter((u) => u.phase === "uploading" || u.phase === "extracting").length;
  const queuedCount = items.filter((u) => u.phase === "queued").length;

  return (
    <div className="bg-paper border border-line rounded-xl overflow-hidden flex flex-col">
      <header className="flex items-center justify-between px-4 py-3.5 border-b border-line-2 font-mono text-[10.5px] text-ink-3 tracking-[0.08em] uppercase font-medium">
        <span>Activity</span>
        {inFlight.length > 0 ? (
          <LiveIndicator active={activeCount} queued={queuedCount} />
        ) : done.length > 0 ? (
          <span className="text-ink-3 normal-case tracking-[0.04em] text-[11px]">
            {done.length} processed
          </span>
        ) : null}
      </header>

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {inFlight.length > 0 && (
            <Group label="Processing">
              {inFlight.map((u) => (
                <InFlightRow key={u.id} item={u} />
              ))}
            </Group>
          )}
          {done.length > 0 && (
            <Group label="Just processed in this session" topBorder={inFlight.length > 0}>
              {done.map((u) => (
                <DoneRow key={u.id} item={u} />
              ))}
            </Group>
          )}
        </>
      )}
    </div>
  );
}

function LiveIndicator({ active, queued }: { active: number; queued: number }) {
  return (
    <span className="inline-flex items-center gap-2 text-accent normal-case tracking-[0.04em] text-[11px]">
      <span className="w-[6px] h-[6px] rounded-full bg-accent-2 shadow-[0_0_0_3px_rgba(45,106,79,0.16)] animate-[pulse_1.8s_ease-in-out_infinite]" />
      {active > 0 && `${active} active`}
      {active > 0 && queued > 0 && " · "}
      {queued > 0 && `${queued} queued`}
    </span>
  );
}

function Group({
  label,
  topBorder,
  children,
}: {
  label: string;
  topBorder?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={cn(topBorder && "border-t border-line-2")}>
      <div className="px-4 pt-2 pb-1.5 font-mono text-[9.5px] text-ink-3 tracking-[0.07em] uppercase">
        {label}
      </div>
      <div className="flex flex-col">{children}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="px-4 py-8 text-center text-[12.5px] text-ink-3 leading-relaxed">
      <span className="font-serif italic text-ink-4 text-[14px] block mb-1">
        Nothing yet
      </span>
      Drag a PDF or click the drop zone to start.
    </div>
  );
}

function InFlightRow({ item }: { item: UploadState }) {
  const elapsed = useElapsedSeconds(item.id);

  if (item.phase === "queued") {
    return (
      <Row>
        <Thumb />
        <Meta name={item.file.name}>
          <span className="text-ink-3 font-mono text-[10.5px] tracking-[0.04em]">
            queued
          </span>
        </Meta>
        <span className="font-mono text-[11px] text-ink-3 font-medium tabular-nums">—</span>
        <DottedRail />
      </Row>
    );
  }

  const verbing = item.phase === "uploading" ? "uploading" : "extracting";

  return (
    <Row>
      <Thumb />
      <Meta name={item.file.name}>
        <span className="text-accent font-mono text-[10.5px] tracking-[0.04em] inline-flex items-center gap-1.5">
          <Spinner />
          {verbing}
          <span className="text-ink-3">· {elapsed.toFixed(1)}s elapsed</span>
        </span>
      </Meta>
      <IndeterminateRail />
    </Row>
  );
}

function DoneRow({ item }: { item: UploadState }) {
  if (item.phase !== "completed" && item.phase !== "failed") return null;

  const isOk = item.phase === "completed";
  const extractionId =
    item.phase === "completed" ? item.extractionId : item.extractionId ?? null;

  const sub = isOk
    ? "extracted"
    : `failed${item.code ? ` · ${item.code}` : ""}`;

  return (
    <Row>
      <Thumb />
      <Meta name={item.file.name}>
        <span
          className={cn(
            "font-mono text-[10.5px] tracking-[0.04em]",
            isOk ? "text-accent-2" : "text-error",
          )}
        >
          {isOk ? "✓" : "✕"} {sub}
        </span>
      </Meta>
      {isOk && extractionId ? (
        <Link
          href={`/review/${extractionId}`}
          className="inline-flex items-center gap-1.5 border border-line bg-paper text-ink text-[11.5px] font-medium tracking-[-0.005em] no-underline rounded-md px-3 py-1.5 hover:border-accent hover:bg-accent-soft hover:text-accent transition-colors group"
        >
          Review
          <svg
            width="11"
            height="11"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            className="group-hover:translate-x-0.5 transition-transform"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </Link>
      ) : (
        <span className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em]">
          —
        </span>
      )}
    </Row>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-2.5 pb-3 text-[12.5px] border-b border-line-2 last:border-b-0 overflow-hidden">
      {children}
    </div>
  );
}

function Thumb() {
  return (
    <span
      className="doc-thumb"
      style={{ width: 18, height: 22, fontSize: 5, paddingBottom: 1 }}
    />
  );
}

function Meta({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 flex flex-col gap-0.5">
      <span className="font-medium text-ink text-[12.5px] tracking-[-0.005em] overflow-hidden text-ellipsis whitespace-nowrap">
        {name}
      </span>
      {children}
    </div>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block w-[9px] h-[9px] rounded-full border-[1.4px] border-accent-soft border-t-accent animate-[spin_0.8s_linear_infinite]"
    />
  );
}

function IndeterminateRail() {
  return (
    <span className="absolute left-4 right-4 bottom-0 h-[2px] bg-line-3 overflow-hidden rounded-[1px]">
      <span className="absolute top-0 h-full w-2/5 rounded-[1px] bg-gradient-to-r from-transparent via-accent to-transparent animate-[upIndeterminate_1.2s_ease-in-out_infinite]" />
    </span>
  );
}

function DottedRail() {
  return (
    <span
      className="absolute left-4 right-4 bottom-0 h-[1px] [background-image:linear-gradient(90deg,var(--color-line)_50%,transparent_50%)] [background-size:6px_1px] [background-repeat:repeat-x]"
      aria-hidden="true"
    />
  );
}

/**
 * Tracks how long the row has been alive in seconds. We can't read the
 * useUpload internal timestamps, so we time from the first render of
 * THIS component for THIS id — close enough; the user sees motion.
 */
function useElapsedSeconds(id: string): number {
  const startRef = useRef<number | null>(null);
  const [, force] = useState(0);

  if (startRef.current === null) {
    startRef.current = performance.now();
  }

  useEffect(() => {
    const t = setInterval(() => force((x) => x + 1), 200);
    return () => clearInterval(t);
    // We deliberately don't depend on id; component remounts per id.
  }, []);

  return startRef.current === null ? 0 : (performance.now() - startRef.current) / 1000;
}
