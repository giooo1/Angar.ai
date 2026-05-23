import {
  DocumentsIcon,
  ReviewIcon,
  SettingsIcon,
  UploadIcon,
} from "@/components/ui/icons";
import type { OrganizationDTO } from "@/lib/api-types";
import { NavItem } from "./nav-item";
import { UsageCard } from "./usage-card";

type Props = {
  organization: OrganizationDTO;
  documentsCount: number;
};

/**
 * Left sidebar. 240px wide, sticky to the viewport, with brand mark,
 * primary nav (Upload / Documents / Review queue), secondary nav
 * (Settings), and the usage card pinned to the bottom.
 *
 * Per the design in App.html. Counts on the nav items are hardcoded
 * for now; will read from the backend in step 7 (Dashboard). Usage
 * card is wired to the real org quota as of step 6.
 */
export function Sidebar({ organization, documentsCount }: Props) {
  const planLabel = organization.plan === "free" ? "Free" : organization.plan;

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
        <NavItem
          href="/dashboard"
          icon={<DocumentsIcon />}
          count={documentsCount.toLocaleString()}
        >
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

      <UsageCard
        used={organization.monthly_extractions_used}
        total={organization.monthly_extraction_quota}
        plan={planLabel}
      />
    </aside>
  );
}
