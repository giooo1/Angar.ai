import {
  DocumentsIcon,
  ReviewIcon,
  SettingsIcon,
  UploadIcon,
} from "@/components/ui/icons";
import { NavItem } from "./nav-item";
import { UsageCard } from "./usage-card";

/**
 * Left sidebar. 240px wide, sticky to the viewport, with brand mark,
 * primary nav (Upload / Documents / Review queue), secondary nav
 * (Settings), and the usage card pinned to the bottom.
 *
 * Per the design in App.html. Counts on the nav items are hardcoded
 * for now; will read from the backend in step 7 (Dashboard).
 */
export function Sidebar() {
  return (
    <aside className="bg-paper-2 border-r border-line flex flex-col px-3.5 py-4 pb-3.5 sticky top-0 h-screen">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-2.5 pb-4 pt-1.5 text-base font-medium tracking-[-0.015em]">
        <div className="brand-mark" />
        <span>
          Angar
          <span className="text-accent font-semibold">.ai</span>
        </span>
      </div>

      {/* Primary nav */}
      <div className="flex flex-col gap-px">
        <NavItem href="/upload" icon={<UploadIcon />}>
          Upload
        </NavItem>
        <NavItem href="/dashboard" icon={<DocumentsIcon />} count="1,408">
          Documents
        </NavItem>
        <NavItem href="/review" icon={<ReviewIcon />} count={3}>
          Review queue
        </NavItem>
      </div>

      {/* Secondary nav */}
      <div className="flex flex-col gap-px mt-3.5">
        <NavItem href="/settings" icon={<SettingsIcon />}>
          Settings
        </NavItem>
      </div>

      <UsageCard used={47} total={200} plan="Pro" />
    </aside>
  );
}
