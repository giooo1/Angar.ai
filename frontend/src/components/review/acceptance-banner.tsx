import { cn } from "@/lib/utils";

type Props = {
  accepted: boolean;
  rejectionReason: string | null;
  overall: number | null;
  confidentCount: number;
  needsReviewCount: number;
};

/**
 * Top banner on the right pane of Review v2. Green when the canonical
 * is accepted; red-tinted error tone when rejected. Right side shows
 * the mean of `field_confidence` as a single big percentage.
 */
export function AcceptanceBanner({
  accepted,
  rejectionReason,
  overall,
  confidentCount,
  needsReviewCount,
}: Props) {
  const isAccepted = accepted;
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 p-4 rounded-xl border",
        isAccepted
          ? "bg-accent-soft border-accent/20 text-accent"
          : "bg-error-soft border-error/22 text-[#7a201d]",
      )}
    >
      <div className="flex items-start gap-3 min-w-0">
        <div
          className={cn(
            "w-[30px] h-[30px] rounded-full bg-paper border-[1.5px] grid place-items-center flex-none font-bold text-[14px]",
            isAccepted ? "border-accent text-accent" : "border-error text-error",
          )}
        >
          {isAccepted ? "✓" : "!"}
        </div>
        <div className="min-w-0">
          <p
            className={cn(
              "font-serif text-[16px] font-medium tracking-[-0.01em] leading-tight m-0 mb-0.5",
            )}
          >
            {isAccepted ? "Document accepted" : "Document rejected"}
          </p>
          <p
            className={cn(
              "text-[12.5px] m-0 leading-[1.45]",
              isAccepted ? "text-accent-2" : "text-[#7a201d]/85",
            )}
          >
            {isAccepted
              ? `${confidentCount} of ${
                  confidentCount + needsReviewCount
                } fields confident.` +
                (needsReviewCount > 0
                  ? ` ${needsReviewCount} need review — highlighted below.`
                  : "")
              : rejectionReason ?? "See extraction notes for the rejection reason."}
          </p>
        </div>
      </div>
      {overall !== null && (
        <div className="flex-none text-right">
          <div className="font-mono text-[9.5px] tracking-[0.08em] uppercase opacity-65">
            Overall
          </div>
          <div className="font-serif text-[22px] font-medium tracking-[-0.015em] leading-none mt-0.5">
            {(overall * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
}
