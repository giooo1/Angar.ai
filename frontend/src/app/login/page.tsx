import Link from "next/link";

import { AuthCard } from "@/components/auth/auth-card";
import { LoginForm } from "@/components/auth/login-form";

type SearchParams = Promise<{ next?: string }>;

export default async function LoginPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const next = params.next ?? "/upload";

  return (
    <AuthCard
      title="Welcome"
      titleAccent="back"
      subtitle="Sign in to keep extracting Georgian invoices into structured data."
      footer={
        <>
          New here?{" "}
          <Link href="/signup" className="text-accent font-medium no-underline hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <LoginForm next={next} />
    </AuthCard>
  );
}
