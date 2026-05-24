import { redirect } from "next/navigation";

import { LandingHero } from "@/components/landing/landing-hero";
import { LandingNav } from "@/components/landing/landing-nav";
import { getServerSession } from "@/lib/auth";

/**
 * Root `/` — closed-beta landing page.
 *
 * Logged-in visitors are bounced to `/upload` server-side so the
 * page never flickers. Anonymous visitors see the editorial hero
 * with the live-extraction animation (CSS-only) and the closed-beta
 * messaging in Mkhedruli per `Hero v2.html`.
 */
export default async function Home() {
  const session = await getServerSession();
  if (session) {
    redirect("/upload");
  }

  return (
    <div className="min-h-screen bg-bg">
      <LandingNav />
      <LandingHero />
    </div>
  );
}
