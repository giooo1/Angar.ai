"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, Thumbnail, pdfjs } from "react-pdf";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { cn } from "@/lib/utils";
import { useDocumentFile } from "@/hooks/use-document-file";

// Self-hosted worker (copied into /public, version-pinned to pdfjs-dist).
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
const ZOOM_STEP = 0.25;
const RAIL_W = 96; // thumbnail rail width
const GAP = 12;

type Props = {
  documentId: string;
  filename: string;
  /** Rendered inside the fullscreen overlay — drops the rounded card chrome
   *  and lets the viewer fill the available height. */
  fullscreen?: boolean;
  /** Toggle fullscreen. When provided the control bar shows the button. */
  onToggleFullscreen?: () => void;
  /** Extra controls on the right of the bar (e.g. a close button in fullscreen). */
  trailing?: React.ReactNode;
  /** When false, keyboard shortcuts are ignored (e.g. the split viewer while
   *  the fullscreen overlay is open). Defaults to true. */
  active?: boolean;
};

/**
 * Controlled PDF/image viewer for the review screen. Renders via react-pdf
 * (pdfjs) with a fit-to-width default — the page fills its pane at zoom 1 and
 * the user zooms in for detail. Replaces the old native-iframe viewer entirely;
 * no browser PDF UI is shown. Our own minimal control bar lives on top.
 *
 * Keyboard (ignored while a field is being edited): +/- zoom, ←/→ page,
 * r rotate, f fullscreen.
 */
export function PdfViewer({ documentId, filename, fullscreen, onToggleFullscreen, trailing, active = true }: Props) {
  const { blobUrl, isImage, loading, error } = useDocumentFile(documentId);

  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [zoom, setZoom] = useState(1); // 1 == fit-to-width
  const [rotation, setRotation] = useState(0);
  const [railOpen, setRailOpen] = useState(false);
  const [areaWidth, setAreaWidth] = useState(0);

  const areaRef = useRef<HTMLDivElement>(null);

  // Measure the scroll container's content width so the page can fit-to-width.
  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      if (w > 0) setAreaWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const multipage = numPages > 1;
  const zoomIn = useCallback(() => setZoom((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2))), []);
  const zoomOut = useCallback(() => setZoom((z) => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2))), []);
  const resetZoom = useCallback(() => setZoom(1), []);
  const rotate = useCallback(() => setRotation((r) => (r + 90) % 360), []);
  const prevPage = useCallback(() => setPageNumber((p) => Math.max(1, p - 1)), []);
  const nextPage = useCallback(() => setPageNumber((p) => Math.min(numPages || 1, p + 1)), [numPages]);

  // Keyboard shortcuts — suppressed while editing a field so typing values
  // doesn't trigger zoom/rotate.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!active) return;
      const el = document.activeElement as HTMLElement | null;
      if (el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))) {
        return;
      }
      switch (e.key) {
        case "+":
        case "=":
          e.preventDefault();
          zoomIn();
          break;
        case "-":
          e.preventDefault();
          zoomOut();
          break;
        case "ArrowLeft":
          if (numPages > 1) {
            e.preventDefault();
            prevPage();
          }
          break;
        case "ArrowRight":
          if (numPages > 1) {
            e.preventDefault();
            nextPage();
          }
          break;
        case "r":
        case "R":
          rotate();
          break;
        case "f":
        case "F":
          onToggleFullscreen?.();
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, numPages, zoomIn, zoomOut, prevPage, nextPage, rotate, onToggleFullscreen]);

  const showRail = !isImage && multipage && railOpen;
  const baseWidth = Math.max(0, areaWidth - (showRail ? RAIL_W + GAP : 0));
  const pageWidth = baseWidth > 0 ? baseWidth * zoom : undefined;

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden",
        fullscreen
          ? "h-full bg-paper-2"
          : "bg-paper-2 border border-line rounded-xl sticky top-6 max-h-[calc(100vh-48px)]",
      )}
    >
      <ControlBar
        page={pageNumber}
        numPages={numPages}
        multipage={multipage}
        railOpen={railOpen}
        onToggleRail={() => setRailOpen((v) => !v)}
        zoom={zoom}
        onPrev={prevPage}
        onNext={nextPage}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onResetZoom={resetZoom}
        onRotate={rotate}
        onToggleFullscreen={onToggleFullscreen}
        fullscreen={fullscreen}
        trailing={trailing}
      />

      <div
        ref={areaRef}
        className="flex-1 overflow-auto p-4 [background:radial-gradient(circle_at_10%_10%,rgba(0,0,0,0.025),transparent_50%),radial-gradient(circle_at_90%_90%,rgba(0,0,0,0.02),transparent_50%),var(--color-paper-2)]"
      >
        {error ? (
          <Centered>Couldn&apos;t load the document. {error}</Centered>
        ) : loading || !blobUrl ? (
          <Centered>Loading document…</Centered>
        ) : isImage ? (
          <div className="mx-auto" style={{ width: pageWidth }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={blobUrl}
              alt={`Document preview: ${filename}`}
              style={{ width: "100%", transform: `rotate(${rotation}deg)`, transition: "width 120ms ease" }}
              className="bg-paper rounded shadow-[0_30px_60px_-30px_rgba(20,15,5,0.22)] border border-line-2"
            />
          </div>
        ) : (
          <Document
            file={blobUrl}
            onLoadSuccess={({ numPages: n }) => {
              setNumPages(n);
              setPageNumber((p) => Math.min(p, n));
            }}
            loading={<Centered>Loading document…</Centered>}
            error={<Centered>Couldn&apos;t render this PDF.</Centered>}
            noData={<Centered>No document.</Centered>}
          >
            <div className="flex items-start justify-center" style={{ gap: GAP }}>
              {showRail && (
                <div className="flex-none flex flex-col gap-2" style={{ width: RAIL_W }}>
                  {Array.from({ length: numPages }, (_, i) => i + 1).map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setPageNumber(n)}
                      className={cn(
                        "rounded-md overflow-hidden border bg-paper cursor-pointer transition-colors",
                        n === pageNumber ? "border-accent ring-2 ring-accent-soft" : "border-line-2 hover:border-ink-3",
                      )}
                      title={`Page ${n}`}
                    >
                      <Thumbnail pageNumber={n} width={RAIL_W - 8} />
                    </button>
                  ))}
                </div>
              )}
              {pageWidth ? (
                <div style={{ width: pageWidth }}>
                  <Page
                    pageNumber={pageNumber}
                    width={pageWidth}
                    rotate={rotation}
                    renderTextLayer
                    renderAnnotationLayer
                    className="!bg-paper rounded shadow-[0_30px_60px_-30px_rgba(20,15,5,0.22),0_8px_20px_-10px_rgba(20,15,5,0.08)] overflow-hidden [&_canvas]:!rounded"
                    loading={<Centered>Rendering…</Centered>}
                  />
                </div>
              ) : null}
            </div>
          </Document>
        )}
      </div>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid place-items-center min-h-[320px] text-[12.5px] text-ink-3 font-mono">
      {children}
    </div>
  );
}

type ControlBarProps = {
  page: number;
  numPages: number;
  multipage: boolean;
  railOpen: boolean;
  onToggleRail: () => void;
  zoom: number;
  onPrev: () => void;
  onNext: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
  onRotate: () => void;
  onToggleFullscreen?: () => void;
  fullscreen?: boolean;
  trailing?: React.ReactNode;
};

function ControlBar({
  page,
  numPages,
  multipage,
  railOpen,
  onToggleRail,
  zoom,
  onPrev,
  onNext,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onRotate,
  onToggleFullscreen,
  fullscreen,
  trailing,
}: ControlBarProps) {
  return (
    <div className="flex items-center justify-between gap-2.5 px-3 py-2 border-b border-line-2 bg-paper">
      <div className="flex items-center gap-1.5">
        {multipage && (
          <>
            <IconBtn label={railOpen ? "Hide thumbnails" : "Show thumbnails"} onClick={onToggleRail} outlined={railOpen}>
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <path d="M14 5h7M14 9h7M14 16h7M14 20h7" />
            </IconBtn>
            <div className="flex items-center gap-0.5">
              <IconBtn label="Previous page" onClick={onPrev} disabled={page <= 1}>
                <path d="M15 18l-6-6 6-6" />
              </IconBtn>
              <span className="px-1.5 font-mono text-[11px] text-ink tabular-nums">
                {page} / {numPages}
              </span>
              <IconBtn label="Next page" onClick={onNext} disabled={page >= numPages}>
                <path d="M9 18l6-6-6-6" />
              </IconBtn>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <div className="flex items-center gap-0.5 border border-line rounded-md p-0.5 bg-paper-2">
          <IconBtn label="Zoom out" onClick={onZoomOut} disabled={zoom <= ZOOM_MIN}>
            <path d="M5 12h14" />
          </IconBtn>
          <button
            type="button"
            onClick={onResetZoom}
            title="Reset to fit width"
            className="px-1.5 font-mono text-[11px] text-ink font-medium tabular-nums hover:text-accent cursor-pointer min-w-[44px]"
          >
            {Math.round(zoom * 100)}%
          </button>
          <IconBtn label="Zoom in" onClick={onZoomIn} disabled={zoom >= ZOOM_MAX}>
            <path d="M12 5v14M5 12h14" />
          </IconBtn>
        </div>
        <IconBtn
          label="Fit to width"
          onClick={onResetZoom}
          disabled={zoom === 1}
          outlined
        >
          <path d="M8 12H3m0 0l3-3m-3 3l3 3" />
          <path d="M16 12h5m0 0l-3-3m3 3l-3 3" />
        </IconBtn>
        <IconBtn label="Rotate 90°" onClick={onRotate} outlined>
          <path d="M21 12a9 9 0 11-3-6.7L21 8" />
          <path d="M21 3v5h-5" />
        </IconBtn>
        {onToggleFullscreen && (
          <IconBtn
            label={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            onClick={onToggleFullscreen}
            outlined
          >
            {fullscreen ? (
              <path d="M9 9H4M9 9V4M15 9h5M15 9V4M9 15H4M9 15v5M15 15h5M15 15v5" />
            ) : (
              <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
            )}
          </IconBtn>
        )}
        {trailing}
      </div>
    </div>
  );
}

function IconBtn({
  label,
  onClick,
  disabled,
  outlined,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  outlined?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={cn(
        "w-[26px] h-[26px] rounded-md grid place-items-center text-ink-2 transition-colors cursor-pointer",
        "hover:bg-paper-2 hover:text-ink disabled:opacity-35 disabled:cursor-not-allowed disabled:hover:bg-transparent",
        outlined && "border border-line bg-paper",
      )}
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
        {children}
      </svg>
    </button>
  );
}
