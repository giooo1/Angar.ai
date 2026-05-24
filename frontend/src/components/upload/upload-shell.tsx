"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { GridIcon, MailIcon } from "@/components/ui/icons";
import type { OrganizationDTO } from "@/lib/api-types";
import { ActivityCard } from "./activity-card";
import { TipsPanel } from "./tips-panel";
import { UploadZone } from "./upload-zone";
import { UsagePanel } from "./usage-panel";
import { useUpload } from "@/hooks/use-upload";

type Props = {
  organization: OrganizationDTO;
};

/**
 * Client shell for the Upload screen. The server `page.tsx` fetches the
 * session and passes the org down so we can render live quota and an
 * exhausted state without a client-side /me roundtrip.
 *
 * On each completed upload (or 429 quota refusal) we call
 * `router.refresh()` so the server-rendered layout + this page re-pick
 * the fresh quota numbers without a hard reload.
 */
export function UploadShell({ organization }: Props) {
  const router = useRouter();
  const { uploads, addFiles } = useUpload();

  // Re-pull server data when an upload completes (sidebar tick) or when
  // the backend rejects with QUOTA_EXHAUSTED (so the empty state kicks in).
  const completedCount = uploads.filter((u) => u.phase === "completed").length;
  const lastQuotaRejectId = useMemo(() => {
    const hit = [...uploads].reverse().find(
      (u) => u.phase === "failed" && u.code === "QUOTA_EXHAUSTED",
    );
    return hit?.id ?? null;
  }, [uploads]);

  useEffect(() => {
    if (completedCount > 0 || lastQuotaRejectId !== null) {
      router.refresh();
    }
  }, [completedCount, lastQuotaRejectId, router]);

  const used = organization.monthly_extractions_used;
  const total = organization.monthly_extraction_quota;
  const exhausted = used >= total;

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
          {exhausted ? (
            <QuotaExhausted
              total={total}
              resetsAtIso={organization.quota_reset_at}
            />
          ) : (
            <UploadZone onFiles={addFiles} />
          )}
        </div>

        {/* RIGHT */}
        <div className="flex flex-col gap-[18px]">
          <UsagePanelWired organization={organization} />
          <ActivityCard items={uploads} />
          <TipsPanel />
        </div>
      </div>
    </main>
  );
}

function UsagePanelWired({ organization }: { organization: OrganizationDTO }) {
  const used = organization.monthly_extractions_used;
  const total = organization.monthly_extraction_quota;
  const resetsAt = new Date(organization.quota_reset_at);
  const now = new Date();
  const resetsInDays = Math.max(
    0,
    Math.ceil((resetsAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)),
  );
  const monthLabel = resetsAt.toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
  const planLabel = organization.plan === "free" ? "Free" : organization.plan;

  return (
    <UsagePanel
      used={used}
      total={total}
      plan={planLabel}
      monthLabel={monthLabel}
      resetsInDays={resetsInDays}
    />
  );
}

function QuotaExhausted({
  total,
  resetsAtIso,
}: {
  total: number;
  resetsAtIso: string;
}) {
  const resetsAt = new Date(resetsAtIso);
  const formatted = resetsAt.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="bg-paper border border-line rounded-xl p-10 text-center">
      <div className="font-serif text-[26px] tracking-[-0.02em] text-ink mb-2">
        Monthly quota reached
      </div>
      <p className="text-[14px] text-ink-3 max-w-[420px] mx-auto mb-1">
        You&apos;ve used all {total} extractions for this billing cycle.
      </p>
      <p className="text-[14px] text-ink-3">
        Your quota resets on{" "}
        <span className="font-medium text-ink">{formatted}</span>.
      </p>
    </div>
  );
}
