"use client";

import { createContext, useContext } from "react";

/**
 * Edit plumbing for the review screen. Field rows and table cells stay
 * uncontrolled `contentEditable` (so the caret never jumps); on blur they
 * read their own text and push it up through one of these callbacks. The
 * provider (ReviewBody) accumulates edits into a draft canonical and saves
 * it on demand.
 *
 * Outside a provider the callbacks are no-ops and `editable` is false, so
 * the leaf components remain usable in non-editing contexts.
 */
export type ReviewEditContextValue = {
  /** Set a dotted path on the draft, e.g. "seller.tin", "grand_total.amount".
   *  `null` clears the field. */
  updateField: (path: string, value: string | null) => void;
  /** Set a (possibly dotted) key on a line item, e.g. updateItem(0, "total.amount", "90"). */
  updateItem: (index: number, key: string, value: string | null) => void;
  editable: boolean;
};

const noop: ReviewEditContextValue = {
  updateField: () => {},
  updateItem: () => {},
  editable: false,
};

const ReviewEditContext = createContext<ReviewEditContextValue>(noop);

export const ReviewEditProvider = ReviewEditContext.Provider;

export function useReviewEdit(): ReviewEditContextValue {
  return useContext(ReviewEditContext);
}

/**
 * Normalize a contentEditable's text into a value for the draft. Trims, and
 * treats the empty string and the "—" placeholder as a cleared field (null).
 */
export function commitText(raw: string): string | null {
  const t = raw.replace(/ /g, " ").trim();
  return t === "" || t === "—" ? null : t;
}

/** Mutate `obj` so that the dotted `path` holds `value`, creating intermediate
 *  objects as needed. */
export function setByPath(obj: Record<string, unknown>, path: string, value: unknown): void {
  const keys = path.split(".");
  let cur: Record<string, unknown> = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i];
    if (cur[k] == null || typeof cur[k] !== "object") cur[k] = {};
    cur = cur[k] as Record<string, unknown>;
  }
  cur[keys[keys.length - 1]] = value;
}
