"use client";

import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { GridIcon, MailIcon } from "@/components/ui/icons";
import { RecentUploads } from "@/components/upload/recent-uploads";
import { TipsPanel } from "@/components/upload/tips-panel";
import { UploadQueue } from "@/components/upload/upload-queue";
import { UploadZone } from "@/components/upload/upload-zone";
import { UsagePanel } from "@/components/upload/usage-panel";
import { useUpload } from "@/hooks/use-upload";

/**
 * Upload screen — Phase 4 step 3.
 *
 * Composition follows App.html `<section data-screen="upload">`:
 *   screen-head:  title + bulk-upload / from-email buttons
 *   up-grid:      drop zone (left) | side panels (right)
 *
 * State lives in the useUpload hook. `inFlight` drives the queue below
 * the drop zone; `recent` drives the right-column recent-uploads list.
 */
export default function UploadPage() {
  const { uploads, addFiles } = useUpload();

  const { inFlight, recent } = useMemo(() => {
    const inFlight = uploads.filter(
      (u) =>
        u.phase === "queued" ||
        u.phase === "uploading" ||
        u.phase === "extracting",
    );
    const recent = uploads.filter(
      (u) => u.phase === "completed" || u.phase === "failed",
    );
    return { inFlight, recent };
  }, [uploads]);

  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      {/* Screen head */}
      <div className="flex items-start justify-between gap-8 mb-7 flex-wrap">
        <div className="max-w-[720px] flex-1 min-w-0">
          <h1 className="font-serif text-[32px] tracking-[-0.02em] font-normal leading-tight m-0 mb-2.5">
            ატვირთე დოკუმენტი
            <br />
            <em className="italic text-accent not-italic font-normal">
              გადააქცე სტრუქტურირებულ მონაცემებად
            </em>
          </h1>
          <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0">
            ფაქტურები, ზედნადებები, ან რომელიმე საგადასახადო დოკუმენტი — Angar
            წაიკითხავს და გადააქცევს სტრუქტურირებულ მონაცემებად.
          </p>
        </div>
        <div className="flex gap-2.5">
          <Button variant="secondary" type="button" disabled>
            <GridIcon size={14} />
            Bulk upload
          </Button>
          <Button variant="secondary" type="button" disabled>
            <MailIcon size={14} />
            From email
          </Button>
        </div>
      </div>

      {/* Body grid */}
      <div className="grid grid-cols-[1.4fr_1fr] gap-6 items-start">
        {/* LEFT */}
        <div>
          <UploadZone onFiles={addFiles} />
          <UploadQueue items={inFlight} />
        </div>

        {/* RIGHT */}
        <div className="flex flex-col gap-[18px]">
          <UsagePanel used={47} total={200} plan="Pro" />
          <RecentUploads items={recent} />
          <TipsPanel />
        </div>
      </div>
    </main>
  );
}
