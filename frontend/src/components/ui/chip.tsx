import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "green" | "warn" | "error";

type Props = HTMLAttributes<HTMLSpanElement> & {
  variant?: Variant;
  /** Show a colored leading dot. Defaults to true on green/warn/error. */
  dot?: boolean;
};

const variantClasses: Record<Variant, string> = {
  default: "bg-paper-2 border-line-2 text-ink-2",
  green:   "bg-accent-soft text-accent border-[rgba(45,106,79,0.18)]",
  warn:    "bg-warn-soft text-[#7a5a13] border-[rgba(184,136,32,0.25)]",
  error:   "bg-error-soft text-[#7a201d] border-[rgba(184,52,47,0.25)]",
};

const dotColors: Record<Variant, string> = {
  default: "bg-ink-3",
  green:   "bg-accent-2",
  warn:    "bg-warn",
  error:   "bg-error",
};

/**
 * Status pill / tag pattern from the App.html mockup.
 * Used for upload state ("extracting", "done", "failed") and
 * document classifications ("VAT invoice", "B2B", etc.).
 */
export function Chip({
  variant = "default",
  dot,
  className,
  children,
  ...rest
}: Props) {
  const showDot = dot ?? variant !== "default";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded-full",
        "text-[11.5px] font-mono tracking-[0.02em]",
        "border",
        variantClasses[variant],
        className,
      )}
      {...rest}
    >
      {showDot && (
        <span
          className={cn("w-[5px] h-[5px] rounded-full", dotColors[variant])}
        />
      )}
      {children}
    </span>
  );
}
