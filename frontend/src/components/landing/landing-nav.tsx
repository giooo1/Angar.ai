import Link from "next/link";

/**
 * Top nav for the landing page. Brand mark on the left, in-page anchor
 * links + a sign-in link + the primary signup CTA on the right.
 *
 * The "Closed beta" pill next to the wordmark sets the expectation
 * before anyone reads the hero — invite-only product.
 */
export function LandingNav() {
  return (
    <nav className="relative z-[5] max-w-[1680px] mx-auto px-14 py-[22px] flex items-center justify-between border-b border-line">
      <div className="flex items-center gap-2.5 font-medium tracking-[-0.015em] text-[17px]">
        <div className="brand-mark" />
        <span>
          Angar
          <span className="text-accent font-semibold">.ai</span>
        </span>
        <span className="ml-2 px-1.5 py-0.5 rounded bg-ink text-paper font-mono text-[8.5px] tracking-[0.06em] uppercase font-medium">
          Closed beta
        </span>
      </div>

      <div className="hidden md:flex gap-[30px] text-[14px] text-ink-2 font-[450]">
        <a href="#product" className="text-inherit no-underline hover:text-ink transition-colors">
          პროდუქტი
        </a>
        <a href="#pricing" className="text-inherit no-underline hover:text-ink transition-colors">
          ფასები
        </a>
        <a href="#docs" className="text-inherit no-underline hover:text-ink transition-colors">
          დოკუმენტაცია
        </a>
      </div>

      <div className="flex gap-2.5 items-center text-[14px]">
        <Link
          href="/login"
          className="text-ink-2 no-underline font-[450] hover:text-ink transition-colors"
        >
          შესვლა
        </Link>
        <Link
          href="/signup"
          className="appearance-none border-0 cursor-pointer font-medium px-4 py-2.5 rounded-lg bg-ink text-bg text-[13.5px] tracking-[-0.005em] no-underline hover:bg-[#2a3140] transition-colors"
        >
          დაიწყე უფასოდ
        </Link>
      </div>
    </nav>
  );
}
