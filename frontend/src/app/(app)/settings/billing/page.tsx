import { redirect } from "next/navigation";

import { BillingPlans } from "@/components/billing/billing-plans";
import { getServerSession } from "@/lib/auth";

/**
 * /settings/billing — three plan tiles. Each upgrade button POSTs to
 * /billing/checkout and hard-navigates to the returned Stripe URL.
 *
 * Server component to read the session; the interactive bits live in
 * <BillingPlans> below.
 */
export default async function BillingPage() {
  const session = await getServerSession();
  if (!session) redirect("/login");

  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1000px]">
      <h1 className="font-serif text-[32px] tracking-[-0.02em] font-normal leading-tight m-0 mb-2.5">
        Billing <em className="italic text-accent not-italic font-normal">& plans</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0 mb-7">
        You're on the{" "}
        <span className="font-medium text-ink">
          {session.organization.plan === "free"
            ? "Free"
            : session.organization.plan.charAt(0).toUpperCase() +
              session.organization.plan.slice(1)}
        </span>{" "}
        plan. Subscriptions are billed monthly via Stripe; cancel any time
        from the customer portal.
      </p>
      <BillingPlans
        currentPlan={session.organization.plan}
        emailVerified={session.user.email_verified_at !== null}
      />
    </main>
  );
}
