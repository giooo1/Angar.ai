/**
 * Server-component fetch wrappers around the backend API.
 *
 * The client wrappers in `./api.ts` rely on `credentials: "include"` for
 * cookie transport — that's a browser-only directive and silently does
 * nothing in a Node.js (server-component) context. These wrappers
 * explicitly forward the request's `angar_session` cookie via the
 * `Cookie` header, mirroring `getServerSession` in `./auth.ts`.
 *
 * Use these in async server components. Use `./api.ts` in client code.
 */

import { cookies } from "next/headers";

import { apiBase } from "./api";
import type { ListExtractionsResponse } from "./api-types";

async function sessionCookieHeader(): Promise<string | null> {
  const jar = await cookies();
  const c = jar.get("angar_session");
  return c ? `${c.name}=${c.value}` : null;
}

export async function listExtractionsServer(params: {
  page: number;
  pageSize: number;
}): Promise<ListExtractionsResponse> {
  const cookieHeader = await sessionCookieHeader();
  const qs = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  const res = await fetch(`${apiBase}/api/v1/extractions?${qs}`, {
    cache: "no-store",
    headers: cookieHeader ? { Cookie: cookieHeader } : {},
  });
  if (!res.ok) {
    throw new Error(`listExtractionsServer: HTTP ${res.status}`);
  }
  return (await res.json()) as ListExtractionsResponse;
}

/**
 * Cheap "how many docs does this org have" probe. Asks for page=1
 * page_size=1 and discards the item list — only `total` is interesting.
 * Used by the (app) layout to surface a real count in the sidebar.
 * Returns 0 on any failure so the layout can render without throwing.
 */
export async function getOrgHeaderStats(): Promise<{ documentsTotal: number }> {
  try {
    const { total } = await listExtractionsServer({ page: 1, pageSize: 1 });
    return { documentsTotal: total };
  } catch {
    return { documentsTotal: 0 };
  }
}
