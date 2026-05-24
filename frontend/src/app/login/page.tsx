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
        <div className="flex flex-col gap-2 items-center">
          <div>
            New here?{" "}
            <Link href="/signup" className="text-accent font-medium no-underline hover:underline">
              Create an account
            </Link>
          </div>
          <Link
            href="/auth/request-reset"
            className="text-ink-3 no-underline hover:text-ink text-[12.5px]"
          >
            Forgot your password?
          </Link>
        </div>
      }
    >
      <LoginForm next={next} />
    </AuthCard>
  );
}
