import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "accent";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const variantClasses: Record<Variant, string> = {
  primary:   "bg-ink text-bg hover:bg-[#2a3140]",
  secondary: "bg-paper border border-line text-ink hover:border-ink-3",
  ghost:     "bg-transparent text-ink-2 hover:bg-black/[0.04] hover:text-ink",
  accent:    "bg-accent text-white hover:bg-accent-2",
};

/**
 * Editorial button matching the App.html design.
 * `primary` = dark ink, `secondary` = paper-with-line, `ghost` = subtle,
 * `accent` = deep editorial green for the main call-to-action.
 */
export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", className, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-lg",
        "font-medium text-[13.5px] tracking-[-0.005em] cursor-pointer",
        "border-0 transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        variantClasses[variant],
        className,
      )}
      {...rest}
    />
  );
});
