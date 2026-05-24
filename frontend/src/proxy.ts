import { type NextRequest, NextResponse } from "next/server";

const PROTECTED_PATHS = ["/upload", "/dashboard", "/review", "/settings"];

/**
 * Route protection for the (app) shell. (Next 16 calls this a "proxy";
 * older Next called it "middleware".)
 *
 * The proxy only enforces ONE rule: anonymous visitors to a protected
 * path get bounced to /login with a `next` query param. We do NOT
 * bounce logged-in visitors away from /login or /signup at this layer
 * — a stale (but present) cookie would cause a ping-pong loop with the
 * (app) layout's server-side session check. /login + /signup pages
 * themselves do the proper server-side session check and redirect to
 * /upload only when the backend confirms the cookie is valid.
 *
 * Browser cookies set by localhost:8000 are visible here on
 * localhost:3000 because both share the localhost host.
 */
export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const sessionCookie = req.cookies.get("angar_session");

  const isProtected = PROTECTED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );

  if (isProtected && !sessionCookie) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/upload/:path*",
    "/dashboard/:path*",
    "/review/:path*",
    "/settings/:path*",
  ],
};
