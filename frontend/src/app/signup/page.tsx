import Link from "next/link";
import { redirect } from "next/navigation";

import { AuthCard } from "@/components/auth/auth-card";
import { SignupForm } from "@/components/auth/signup-form";
import { getServerSession } from "@/lib/auth";

export default async function SignupPage() {
  // If the cookie validates server-side, send the user into the app
  // instead of letting them create a second account.
  const session = await getServerSession();
  if (session) {
    redirect("/upload");
  }

  return (
    <AuthCard
      title="Create your"
      titleAccent="workspace"
      subtitle="Set up an account and an organization. You can invite teammates later."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="text-accent font-medium no-underline hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <SignupForm />
    </AuthCard>
  );
}
