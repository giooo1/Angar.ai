"use client";

import { type DragEvent, useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { InfoIcon, PlusIcon, UploadIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

const ACCEPT_ATTR = ".pdf,.jpg,.jpeg,.png,.heic,application/pdf,image/jpeg,image/png,image/heic";

// Document categories Angar handles — decorative hints, not a selectable
// filter (type is auto-detected during extraction).
const DOC_TYPES = ["Invoice", "Waybill", "Receipt", "Contract", "Custom"];

type Props = {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
};

/**
 * Drag-and-drop file picker. Wraps a hidden <input type=file> so clicking
 * the zone or pressing the browse button both open the OS picker.
 *
 * Drag-over state highlights the border + background. Unknown MIME types
 * still flow through to the parent; the backend rejects them with a
 * 415 that the upload hook surfaces as a "failed" state.
 */
export function UploadZone({ onFiles, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      onFiles(Array.from(list));
    },
    [onFiles],
  );

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles, disabled],
  );

  const onDragOver = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      if (disabled) return;
      e.preventDefault();
      setDragOver(true);
    },
    [disabled],
  );

  const onDragLeave = useCallback(() => setDragOver(false), []);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Drop documents or click to browse"
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      className={cn(
        "relative bg-paper rounded-xl border-[1.5px] border-dashed",
        "py-16 px-10 text-center cursor-pointer",
        "min-h-[380px] flex flex-col items-center justify-center gap-3.5",
        "transition-colors duration-150",
        dragOver
          ? "border-accent bg-paper-2"
          : "border-line hover:border-accent hover:bg-paper-2",
        disabled && "opacity-60 cursor-not-allowed",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_ATTR}
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="w-16 h-16 rounded-2xl bg-accent-soft text-accent grid place-items-center mb-1.5">
        <UploadIcon size={28} strokeWidth={1.6} />
      </div>

      <h2 className="font-serif text-[26px] font-normal tracking-[-0.02em] m-0 leading-tight">
        გადმოიტანე ფაილი ან{" "}
        <em className="italic text-accent font-normal">აირჩიე</em>
      </h2>

      <p className="text-sm text-ink-3 max-w-[380px] m-0 text-pretty">
        PDF, JPG, PNG ან HEIC — მაქს. <b className="text-ink font-medium">20MB</b>. ერთდროულად
        შეგიძლია ატვირთო <b className="text-ink font-medium">100-მდე</b> ფაილი.
      </p>

      <div className="mt-2.5 flex gap-2 flex-wrap justify-center">
        {DOC_TYPES.map((t) => (
          <span
            key={t}
            className="px-2.5 py-1 rounded-full bg-paper-2 font-mono text-[10.5px] text-ink-3 tracking-[0.04em] uppercase border border-line-2"
          >
            {t}
          </span>
        ))}
      </div>

      <Button variant="accent" className="mt-2" type="button">
        <PlusIcon size={14} strokeWidth={2} />
        Browse files
      </Button>

      <p className="mt-3 flex items-center justify-center gap-2 text-[12.5px] text-ink-3 max-w-[440px] m-0 leading-snug">
        <InfoIcon size={14} strokeWidth={1.7} className="text-ink-4 shrink-0" />
        დაბალი ხარისხის სკანების მუშავდება — ოღონდ უკეთესია სუფთა PDF.
      </p>
    </div>
  );
}
