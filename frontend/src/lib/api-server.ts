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
  /** Worklist mode: only docs needing attention (not yet approved). */
  pending?: boolean;
  sort?: "newest" | "oldest";
  // Archive filters
  q?: string;
  documentType?: string;
  accepted?: boolean;
  hasCorrections?: boolean;
  dateFrom?: string;
  dateTo?: string;
}): Promise<ListExtractionsResponse> {
  const cookieHeader = await sessionCookieHeader();
  const qs = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.pending) qs.set("pending", "true");
  if (params.sort) qs.set("sort", params.sort);
  if (params.q) qs.set("q", params.q);
  if (params.documentType) qs.set("document_type", params.documentType);
  if (params.accepted !== undefined) qs.set("accepted", String(params.accepted));
  if (params.hasCorrections) qs.set("has_corrections", "true");
  if (params.dateFrom) qs.set("date_from", params.dateFrom);
  if (params.dateTo) qs.set("date_to", params.dateTo);
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
 * Cheap "how many docs need my attention" probe for the nav badge. Asks for
 * the pending worklist with page_size=1 and keeps only `total`. Returns 0 on
 * any failure so the layout renders without throwing.
 */
export async function getOrgHeaderStats(): Promise<{ pendingTotal: number }> {
  try {
    const { total } = await listExtractionsServer({ page: 1, pageSize: 1, pending: true });
    return { pendingTotal: total };
  } catch {
    return { pendingTotal: 0 };
  }
}
