import Link from "next/link";

import { LiveExtractionStage } from "./live-extraction-stage";

/**
 * Editorial split-hero. Left column carries the Mkhedruli copy and the
 * primary + ghost CTAs; right column hosts the animated extraction
 * stage (`<LiveExtractionStage>`).
 *
 * Headline + lede preserved verbatim from `Hero v2.html` per the
 * language conventions memory (Mkhedruli for customer-facing copy).
 */
export function LandingHero() {
  return (
    <main className="relative z-[2]">
      <section className="max-w-[1680px] mx-auto px-14 pt-[88px] pb-[60px] grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] gap-20 items-center">
        <div>
          <h1 className="font-serif text-[clamp(40px,4.2vw,62px)] leading-[1.05] tracking-[-0.03em] font-light m-0 mb-7 text-ink [text-wrap:balance] [hyphens:auto]">
            ატვირთე დოკუმენტი.<br />
            მიიღე{" "}
            <em className="not-italic font-normal text-accent font-serif italic">
              სტრუქტურირებული
            </em>
            <br />
            მონაცემები —{" "}
            <em className="not-italic font-normal text-accent font-serif italic">
              ინსტანტურად.
            </em>
          </h1>

          <p className="text-[17px] leading-[1.55] text-ink-2 max-w-[520px] font-normal m-0 [text-wrap:pretty]">
            AI სისტემა ფაქტურებისთვის, ზედნადებებისთვის
            და სხვა საგადასახადო დოკუმენტებისთვის —
            ინსტანტური ექსტრაქცია.
          </p>

          <div className="flex gap-3.5 mt-9 items-center flex-wrap">
            <Link
              href="/signup"
              className="px-5 py-3.5 text-[14.5px] rounded-[9px] bg-ink text-bg border-0 font-medium tracking-[-0.005em] cursor-pointer inline-flex items-center gap-2 no-underline hover:bg-[#2a3140] hover:-translate-y-px transition-all"
            >
              დაიწყე უფასოდ
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
            <Link
              href="/login"
              className="bg-transparent border-0 text-ink font-medium text-[14.5px] cursor-pointer inline-flex items-center gap-1.5 px-1.5 py-3.5 no-underline group"
            >
              ნახე როგორ მუშაობს
              <span className="transition-transform group-hover:translate-x-[3px]">
                →
              </span>
            </Link>
          </div>
        </div>

        <div className="w-full isolate">
          <LiveExtractionStage />
        </div>
      </section>
    </main>
  );
}
