import type { LineItem } from "@/lib/canonical";
import { moneyText } from "./money-cell";
import { Section } from "./section";

type Props = { items: LineItem[] };

/**
 * Line items rendered as a tight table inside its own Section card.
 * Columns: description (Mkhedruli serif italic per design) · quantity
 * with unit · unit_price · total. Renders nothing when items is empty
 * — callers decide whether to show the section header in that case.
 */
export function LineItemsTable({ items }: Props) {
  if (items.length === 0) return null;

  return (
    <Section badge="L" title="Line items" count={`${items.length} lines`}>
      <table className="w-full border-collapse font-mono">
        <thead>
          <tr>
            <Th>Description</Th>
            <Th align="right">Qty</Th>
            <Th align="right">Unit price</Th>
            <Th align="right">Total</Th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={idx}>
              <Td>
                <span className="font-serif italic text-ink text-[13.5px] font-normal">
                  {item.description}
                </span>
              </Td>
              <Td align="right">
                <span className="font-medium text-ink">
                  {item.quantity}
                  {item.unit ? ` ${item.unit}` : ""}
                </span>
              </Td>
              <Td align="right">
                <span className="font-medium text-ink">
                  {moneyText(item.unit_price) ?? "—"}
                </span>
              </Td>
              <Td align="right">
                <span className="font-medium text-ink">
                  {moneyText(item.total) ?? "—"}
                </span>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function Th({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <th
      className={
        "py-2 px-4 text-[10px] text-ink-3 font-medium tracking-[0.06em] uppercase " +
        "border-b border-line-2 bg-paper-2 " +
        (align === "right" ? "text-right" : "text-left")
      }
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <td
      className={
        "py-2.5 px-4 text-[12px] text-ink-2 border-b border-line-2 last:border-b-0 " +
        (align === "right" ? "text-right" : "text-left")
      }
    >
      {children}
    </td>
  );
}
