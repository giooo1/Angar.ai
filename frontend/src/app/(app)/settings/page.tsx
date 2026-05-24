import Link from "next/link";

/**
 * /settings — placeholder hub. Right now the only real sub-page is
 * billing. Account / organization / data & privacy come later.
 */
export default function SettingsPage() {
  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1000px]">
      <h1 className="font-serif text-3xl leading-tight tracking-[-0.02em] font-normal m-0 mb-2.5">
        <em className="italic text-accent not-italic font-normal">Settings</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0 mb-7">
        Manage your account and subscription.
      </p>
      <div className="flex flex-col gap-2">
        <Link
          href="/settings/billing"
          className="block bg-paper border border-line rounded-xl px-5 py-4 no-underline text-ink hover:bg-paper-2 transition-colors"
        >
          <div className="font-serif text-[17px] tracking-[-0.015em]">Billing & plans</div>
          <div className="text-[12.5px] text-ink-3 mt-0.5">
            Subscription, payment, invoices.
          </div>
        </Link>
      </div>
    </main>
  );
}
