type Props = {
  /** URL to the backend's file endpoint for this document. */
  url: string;
  /** Original filename for the accessibility title. */
  filename: string;
};

/**
 * Left pane of the Review screen — renders the source PDF via a
 * native browser iframe. The browser provides scroll, zoom, and page
 * controls inside the iframe; the buttons we render in the toolbar
 * are visual affordances per the Review v2 design — actual zoom-by-
 * scale-transform is a future enhancement.
 *
 * Image uploads (jpg/png/heic) also render here — browsers handle
 * them inline. HEIC may not render in non-Safari browsers; that's a
 * known caveat we'll address when an accountant actually uploads one.
 */
export function PdfPane({ url, filename }: Props) {
  return (
    <div className="bg-paper-2 border border-line rounded-xl overflow-hidden flex flex-col sticky top-6 max-h-[calc(100vh-48px)]">
      <div className="flex items-center justify-between gap-2.5 px-3 py-2 border-b border-line-2 bg-paper">
        <span className="font-mono text-[10.5px] text-ink-3 tracking-[0.05em]">
          Page <b className="text-ink font-medium">1</b> of 1
        </span>
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-0.5 border border-line rounded-md p-0.5 bg-paper-2">
            <ToolBtn label="Zoom out" iconPath="M5 12h14" />
            <span className="px-1.5 font-mono text-[11px] text-ink font-medium">100%</span>
            <ToolBtn label="Zoom in" iconPath="M12 5v14M5 12h14" />
          </div>
          <ToolBtn
            label="Fit width"
            outlined
            iconPath="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4"
          />
          <ToolBtn
            label="Pan"
            outlined
            iconPath="M18 11V6a2 2 0 00-2-2 2 2 0 00-2 2"
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 [background:radial-gradient(circle_at_10%_10%,rgba(0,0,0,0.025),transparent_50%),radial-gradient(circle_at_90%_90%,rgba(0,0,0,0.02),transparent_50%),var(--color-paper-2)]">
        <iframe
          src={url}
          title={`Document preview: ${filename}`}
          className="w-full bg-paper rounded shadow-[0_30px_60px_-30px_rgba(20,15,5,0.22),0_8px_20px_-10px_rgba(20,15,5,0.08)]"
          style={{ minHeight: 560, border: "1px solid var(--color-line-2)" }}
        />
      </div>
    </div>
  );
}

function ToolBtn({
  label,
  iconPath,
  outlined,
}: {
  label: string;
  iconPath: string;
  outlined?: boolean;
}) {
  return (
    <button
      type="button"
      disabled
      title={label}
      aria-label={label}
      className={
        "w-[26px] h-[26px] rounded-md grid place-items-center text-ink-2 hover:bg-paper-2 transition-colors cursor-not-allowed opacity-80 " +
        (outlined ? "border border-line bg-paper" : "bg-transparent")
      }
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={iconPath} />
      </svg>
    </button>
  );
}
