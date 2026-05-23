import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PlusIcon } from "@/components/ui/icons";
import type { ExtractionStatusResponse } from "@/lib/api-types";
import { DocumentRow } from "./document-row";

type Props = {
  items: ExtractionStatusResponse[];
};

export function DocumentsTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="bg-paper border border-line rounded-xl p-12 text-center">
        <p className="font-serif text-[20px] font-medium text-ink m-0 mb-2">
          No documents yet
        </p>
        <p className="text-[13px] text-ink-3 m-0 mb-5">
          Upload your first invoice to start building your library.
        </p>
        <Link href="/upload">
          <Button variant="accent">
            <PlusIcon size={14} strokeWidth={2} />
            Upload a document
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-paper border border-line rounded-xl overflow-hidden">
      <div className="grid grid-cols-[40px_1fr_120px_220px_140px_auto] gap-3 items-center px-4 py-3 border-b border-line-2 bg-paper-2 font-mono text-[10.5px] text-ink-3 tracking-[0.06em] uppercase">
        <span />
        <span>Document</span>
        <span>Date</span>
        <span>Seller</span>
        <span>Grand total</span>
        <span>Status</span>
      </div>
      {items.map((item) => (
        <DocumentRow key={item.extraction_id} item={item} />
      ))}
    </div>
  );
}
