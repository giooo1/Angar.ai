import type { NextConfig } from "next";

// Same-origin API proxy: the browser calls `/api/*` on the frontend domain and
// Vercel forwards to the backend. This keeps the session cookie first-party to
// the frontend (so getServerSession / the proxy middleware can read it) even
// when the backend is on a different host (Railway). Destination is baked at
// build time from BACKEND_ORIGIN / NEXT_PUBLIC_API_URL.
const backend = (
  process.env.BACKEND_ORIGIN ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
