import { type NextRequest, NextResponse } from "next/server";

const PROTECTED_PATHS = ["/upload", "/dashboard", "/review", "/settings"];
const AUTH_PAGES = ["/login", "/signup"];

/**
 * Route protection for the (app) shell. (Next 16 calls this a "proxy";
 * older Next called it "middleware".)
 *
 * We only check for COOKIE PRESENCE here — the backend is the
 * authority on whether the JWT is valid. Browser cookies set by
 * localhost:8000 are visible to the proxy running on localhost:3000
 * because both share the localhost host.
 *
 * Anonymous visitors get redirected to /login with a `next` query
 * param so the login form can bounce them back. Already-logged-in
 * visitors who land on /login or /signup get bounced to /upload.
 */
export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const sessionCookie = req.cookies.get("angar_session");

  const isProtected = PROTECTED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
  const isAuthPage = AUTH_PAGES.includes(pathname);

  if (isProtected && !sessionCookie) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && sessionCookie) {
    const url = req.nextUrl.clone();
    url.pathname = "/upload";
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
    "/login",
    "/signup",
  ],
};
