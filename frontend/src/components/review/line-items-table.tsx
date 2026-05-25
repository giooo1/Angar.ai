"use client";

import type { LineItem } from "@/lib/canonical";
import { commitText, useReviewEdit } from "./review-edit-context";
import { SectionBlock } from "./section-block";

type Props = { items: LineItem[] };

/**
 * Line items as a table. Each cell is `contentEditable`; on blur it pushes
 * its text up through the edit context keyed by row index + field
 * ("description", "quantity", "unit_price.amount", "total.amount"). Per-line
 * confidence isn't shown for v1.
 */
export function LineItemsTable({ items }: Props) {
  const edit = useReviewEdit();

  return (
    <SectionBlock
      letter="L"
      title="Line items"
      right={
        <span className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em]">
          {items.length} {items.length === 1 ? "line" : "lines"}
        </span>
      }
      bodyClassName="p-0"
    >
      <table className="w-full border-collapse font-mono">
        <thead>
          <tr>
            <Th>Description</Th>
            <Th right>Qty</Th>
            <Th right>Unit price</Th>
            <Th right>Amount</Th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td
                colSpan={4}
                className="px-4 py-6 text-center text-[12.5px] text-ink-3 italic"
              >
                No line items extracted.
              </td>
            </tr>
          ) : (
            items.map((item, idx) => (
              <tr key={idx}>
                <Td
                  idx={idx}
                  itemKey="description"
                  edit={edit}
                  className="!font-serif !italic !text-ink !text-[13.5px] !font-normal"
                >
                  {item.description}
                </Td>
                <Td idx={idx} itemKey="quantity" edit={edit} right>
                  {item.quantity}
                </Td>
                <Td idx={idx} itemKey="unit_price.amount" edit={edit} right>
                  {item.unit_price.amount}
                </Td>
                <Td idx={idx} itemKey="total.amount" edit={edit} right>
                  {item.total.amount}
                </Td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </SectionBlock>
  );
}

function Th({ children, right }: { children: React.ReactNode; right?: boolean }) {
  return (
    <th
      className={
        "py-2.5 px-4 text-[9.5px] text-ink-3 font-medium tracking-[0.06em] uppercase " +
        "border-b border-line-2 bg-paper-2 " +
        (right ? "text-right" : "text-left")
      }
    >
      {children}
    </th>
  );
}

function Td({
  children,
  idx,
  itemKey,
  edit,
  right,
  className,
}: {
  children: React.ReactNode;
  idx: number;
  itemKey: string;
  edit: ReturnType<typeof useReviewEdit>;
  right?: boolean;
  className?: string;
}) {
  return (
    <td
      className={
        "py-2.5 px-4 text-[12px] text-ink-2 border-b border-line-2 last:border-b-0 outline-none focus:bg-paper focus:[box-shadow:inset_0_0_0_1.5px_var(--color-accent)] " +
        (right ? "text-right font-medium text-ink " : "") +
        (className ?? "")
      }
      contentEditable={edit.editable}
      suppressContentEditableWarning
      onBlur={
        edit.editable
          ? (e) => edit.updateItem(idx, itemKey, commitText(e.currentTarget.textContent ?? ""))
          : undefined
      }
    >
      {children}
    </td>
  );
}
