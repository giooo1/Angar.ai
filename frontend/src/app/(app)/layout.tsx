import { redirect } from "next/navigation";

import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { getServerSession } from "@/lib/auth";

/**
 * App shell layout: 240px sidebar + main column with sticky topbar.
 *
 * Server component — fetches the current session and passes it to the
 * Topbar so it can render the real organization name and user initial.
 * If the session fetch fails (cookie missing or backend rejected it),
 * we redirect to /login. The middleware should catch this earlier, but
 * this is defense in depth for the edge case where the cookie exists
 * but the backend can't validate it (e.g. expired token).
 */
export default async function AppShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession();
  if (!session) {
    redirect("/login");
  }

  return (
    <div className="grid grid-cols-[240px_1fr] min-h-screen">
      <Sidebar organization={session.organization} />
      <div className="flex flex-col min-w-0">
        <Topbar user={session.user} organization={session.organization} />
        {children}
      </div>
    </div>
  );
}
