import { redirect } from "next/navigation";

import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { VerificationBanner } from "@/components/shell/verification-banner";
import { getOrgHeaderStats } from "@/lib/api-server";
import { getServerSession } from "@/lib/auth";

/**
 * App shell layout: 240px sidebar + main column with sticky topbar.
 *
 * Server component — fetches the current session and the org-level
 * header stats (documents total for the sidebar count) in parallel,
 * passing both down to the chrome components. If the session fetch
 * fails the middleware should already have caught it, but we redirect
 * here too as defense in depth.
 */
export default async function AppShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, headerStats] = await Promise.all([
    getServerSession(),
    getOrgHeaderStats(),
  ]);
  if (!session) {
    redirect("/login");
  }

  return (
    <div className="grid grid-cols-[240px_1fr] min-h-screen">
      <Sidebar
        organization={session.organization}
        pendingCount={headerStats.pendingTotal}
      />
      <div className="flex flex-col min-w-0">
        {session.user.email_verified_at === null && (
          <VerificationBanner email={session.user.email} />
        )}
        <Topbar user={session.user} organization={session.organization} />
        {children}
      </div>
    </div>
  );
}
