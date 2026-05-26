import Link from "next/link";
import { redirect } from "next/navigation";

import { ProfileForm } from "@/components/settings/profile-form";
import { getServerSession } from "@/lib/auth";

/**
 * /settings — the Profile section (functional) plus the designed left nav.
 * Only Profile and Billing are real today; the rest are placeholders that
 * mirror the App.html design and land when built.
 */
export default async function SettingsPage() {
  const session = await getServerSession();
  if (!session) {
    redirect("/login");
  }

  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1100px]">
      <h1 className="font-serif text-[32px] leading-tight tracking-[-0.02em] font-normal m-0 mb-2.5">
        <em className="italic text-accent not-italic font-normal">Settings</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0 mb-7">
        Profile, organization, billing, and data.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-9 items-start">
        <nav className="flex flex-col gap-0.5 md:sticky md:top-6">
          <span className="block px-3 py-2 rounded-md text-[13.5px] font-medium bg-paper border border-line text-ink shadow-[0_1px_2px_rgba(20,15,5,0.04)]">
            Profile
          </span>
          <Placeholder>Organization</Placeholder>
          <Placeholder>Members</Placeholder>
          <Link
            href="/settings/billing"
            className="block px-3 py-2 rounded-md text-[13.5px] font-[450] text-ink-2 no-underline hover:bg-paper-2 hover:text-ink"
          >
            Billing &amp; plan
          </Link>
          <Placeholder>Data &amp; privacy</Placeholder>
          <Placeholder badge="SOON">API access</Placeholder>
          <Placeholder>Notifications</Placeholder>
        </nav>

        <ProfileForm user={session.user} />
      </div>
    </main>
  );
}

function Placeholder({ children, badge }: { children: React.ReactNode; badge?: string }) {
  return (
    <span
      className="px-3 py-2 rounded-md text-[13.5px] font-[450] text-ink-4 cursor-default select-none"
      title="Coming soon"
    >
      {children}
      {badge && (
        <span className="ml-1.5 font-mono text-[10px] text-ink-3 tracking-[0.04em]">{badge}</span>
      )}
    </span>
  );
}
