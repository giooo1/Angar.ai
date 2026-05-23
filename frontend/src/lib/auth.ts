import { cookies } from "next/headers";

import { apiBase } from "./api";
import type { MeResponse } from "./api-types";

/**
 * Server-side helper to fetch the current session.
 *
 * Used by the (app) layout to populate the topbar without a client
 * round-trip. Forwards the request's cookies to the backend so the
 * authenticated /me endpoint sees them.
 *
 * Returns null when there's no cookie or when the backend rejects it.
 */
export async function getServerSession(): Promise<MeResponse | null> {
  const cookieJar = await cookies();
  const session = cookieJar.get("angar_session");
  if (!session) return null;

  try {
    const res = await fetch(`${apiBase}/api/v1/me`, {
      cache: "no-store",
      headers: { Cookie: `${session.name}=${session.value}` },
    });
    if (!res.ok) return null;
    return (await res.json()) as MeResponse;
  } catch {
    return null;
  }
}
