import { redirect } from "next/navigation";

/**
 * Root `/` — sends the user to `/upload`. Once step 5 (auth) lands,
 * unauthenticated visitors get sent to a sign-in page instead and
 * authenticated visitors continue to `/upload`. Once Hero v2.html
 * lands as a public marketing landing, this becomes the marketing page.
 */
export default function Home() {
  redirect("/upload");
}
