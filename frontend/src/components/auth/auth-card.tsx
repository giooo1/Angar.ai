import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  title: string;
  titleAccent?: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
};

/**
 * Editorial card layout shared by /login and /signup. Cream background,
 * Fraunces headline with an italic accent word, centered card with a
 * paper border. Hero v2.html aesthetic at smaller scale.
 */
export function AuthCard({ title, titleAccent, subtitle, children, footer }: Props) {
  return (
    <main className="min-h-screen bg-bg flex flex-col items-center justify-center px-6 py-12">
      <Link
        href="/"
        className="flex items-center gap-2.5 mb-12 text-base font-medium tracking-[-0.015em] no-underline text-ink"
      >
        <div className="brand-mark" />
        <span>
          Angar
          <span className="text-accent font-semibold">.ai</span>
        </span>
      </Link>

      <div className="w-full max-w-[420px] bg-paper border border-line rounded-xl p-9 shadow-[0_30px_60px_-30px_rgba(20,15,5,0.18),0_8px_20px_-10px_rgba(20,15,5,0.08)]">
        <h1 className="font-serif text-[28px] font-normal tracking-[-0.02em] leading-tight m-0 mb-2">
          {title}
          {titleAccent && (
            <>
              {" "}
              <em className="italic text-accent not-italic font-normal">
                {titleAccent}
              </em>
            </>
          )}
        </h1>
        <p className="text-[14px] text-ink-3 m-0 mb-7 leading-[1.5]">{subtitle}</p>

        {children}

        <div className="mt-7 pt-5 border-t border-line-2 text-center text-[13px] text-ink-3">
          {footer}
        </div>
      </div>
    </main>
  );
}
