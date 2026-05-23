import Link from "next/link";

import { AuthCard } from "@/components/auth/auth-card";
import { SignupForm } from "@/components/auth/signup-form";

export default function SignupPage() {
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
