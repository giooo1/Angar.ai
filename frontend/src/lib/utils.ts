/** Tailwind class-name joiner. Filters falsy entries, joins with a space. */
export function cn(...inputs: Array<string | false | null | undefined>): string {
  return inputs.filter(Boolean).join(" ");
}
