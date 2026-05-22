type Props = {
  /** URL to the backend's file endpoint for this document. */
  url: string;
  /** Original filename for the accessibility title. */
  filename: string;
};

/**
 * Left pane of the Review screen — renders the source PDF via a
 * native browser iframe. The browser provides scroll, zoom, and page
 * controls inside the iframe; we don't reimplement them.
 *
 * Image uploads (jpg/png/heic) also render here — browsers handle
 * them inline. HEIC may not render in non-Safari browsers; that's a
 * known caveat we'll address when an accountant actually uploads one.
 */
export function PdfPane({ url, filename }: Props) {
  return (
    <div className="bg-paper-2 border border-line rounded-xl overflow-hidden flex flex-col min-h-[600px]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-line-2 bg-paper font-mono text-[10.5px] text-ink-3 tracking-[0.05em] uppercase">
        <span>{filename}</span>
        <span>browser native</span>
      </div>
      <iframe
        src={url}
        title={`Document preview: ${filename}`}
        className="flex-1 w-full bg-paper-2"
        style={{ minHeight: 560, border: 0 }}
      />
    </div>
  );
}
