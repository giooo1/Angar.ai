import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";

/**
 * App shell layout: 240px sidebar + main column with sticky topbar.
 * Every authenticated app route (`/upload`, `/dashboard`, `/review`,
 * `/settings`) renders through this layout.
 *
 * Step 5 (auth) wraps this layout with a NextAuth gate; for now the
 * shell renders for any visitor.
 */
export default function AppShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[240px_1fr] min-h-screen">
      <Sidebar />
      <div className="flex flex-col min-w-0">
        <Topbar />
        {children}
      </div>
    </div>
  );
}
