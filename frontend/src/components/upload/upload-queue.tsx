import type { UploadState } from "@/hooks/use-upload";

type Props = {
  /** Files currently in-flight (queued / uploading / extracting). */
  items: UploadState[];
};

const phaseLabel: Record<UploadState["phase"], string> = {
  queued: "queued",
  uploading: "uploading",
  extracting: "extracting",
  completed: "done",
  failed: "failed",
};

/**
 * Strip below the drop zone showing the files currently being processed.
 * Renders nothing when nothing is in flight (avoids an empty "Processing" label).
 */
export function UploadQueue({ items }: Props) {
  if (items.length === 0) return null;

  return (
    <div className="mt-4 flex items-center gap-2.5 flex-wrap">
      <span className="font-mono text-[10.5px] text-ink-3 tracking-[0.06em] uppercase">
        Processing
      </span>
      {items.map((item) => (
        <div
          key={item.id}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-paper border border-line-2 text-[12.5px]"
        >
          <span className="doc-thumb" style={{ width: 18, height: 22 }} />
          <span className="font-medium text-ink">{item.file.name}</span>
          <span className="font-mono text-[10.5px] text-accent tracking-[0.04em]">
            {phaseLabel[item.phase]}
          </span>
        </div>
      ))}
    </div>
  );
}
