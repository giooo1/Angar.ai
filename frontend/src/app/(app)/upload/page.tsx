import { redirect } from "next/navigation";

import { UploadShell } from "@/components/upload/upload-shell";
import { getServerSession } from "@/lib/auth";

/**
 * Upload screen — Phase 4 step 6.
 *
 * Server component: fetches the live session so the page can render
 * real quota numbers and gate the upload form on capacity. The
 * interactive state machine lives in `<UploadShell>` (client).
 */
export default async function UploadPage() {
  const session = await getServerSession();
  if (!session) {
    redirect("/login");
  }
  return <UploadShell organization={session.organization} />;
}
