"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

/**
 * Landing page after Stripe Checkout. Stripe webhooks update plan +
 * quota out-of-band; we just call router.refresh() so the (app) layout
 * re-fetches the org and the sidebar reflects the new tier.
 */
export default function BillingSuccessPage() {
  const router = useRouter();
  useEffect(() => {
    // Give Stripe ~1s to deliver the webhook before refreshing. Worst case
    // the user clicks the button below to re-pull.
    const t = setTimeout(() => router.refresh(), 1000);
    return () => clearTimeout(t);
  }, [router]);

  return (
    <main className="px-10 py-16 w-full max-w-[680px]">
      <h1 className="font-serif text-[32px] tracking-[-0.02em] font-normal leading-tight m-0 mb-2.5">
        Thanks <em className="italic text-accent not-italic font-normal">— you're upgraded</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 m-0 mb-6">
        Your new quota will appear in the sidebar within a few seconds.
        If you don't see it, click below to refresh.
      </p>
      <div className="flex gap-3">
        <Button
          variant="primary"
          type="button"
          onClick={() => router.refresh()}
        >
          Refresh
        </Button>
        <Link href="/upload">
          <Button variant="secondary" type="button">
            Back to upload
          </Button>
        </Link>
      </div>
    </main>
  );
}
