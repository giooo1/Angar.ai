import type { Money } from "@/lib/canonical";

/**
 * Renders a Money value. `null` shows as the FieldRow's `—` placeholder
 * (handled by FieldRow). Empty-string amount also collapses to `—`.
 *
 * Currency printed in mono after the amount; matches the App.html
 * design (`2,891.00 GEL`).
 */
export function moneyText(m: Money | null | undefined): string | null {
  if (!m || !m.amount) return null;
  return `${m.amount} ${m.currency}`;
}

type Props = { money: Money | null | undefined };

export function MoneyCell({ money }: Props) {
  const text = moneyText(money);
  if (text === null) return null;
  return (
    <span className="font-mono text-[13px] text-ink font-semibold tracking-[-0.005em]">
      {text}
    </span>
  );
}
