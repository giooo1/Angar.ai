/**
 * Frontend mirror of `angar_extraction/errors.py:ERROR_COPY`.
 *
 * The backend persists `error_code` on the Extraction row; this map
 * returns the en/ka strings the review screen renders for each.
 * Falls back to the backend's `error_message` when the code is null
 * or unknown.
 */

export type ExtractionErrorCopy = {
  title: string;
  body: string;
};

const COPY: Record<string, ExtractionErrorCopy> = {
  ANTHROPIC_AUTH: {
    title: "Service unavailable",
    body:
      "We couldn't reach the extraction service due to a configuration issue. Your quota was refunded.",
  },
  ANTHROPIC_RATE_LIMIT: {
    title: "Service is busy",
    body:
      "We retried a few times but the extraction service is rate-limiting us. Your quota was refunded — try again in a minute.",
  },
  ANTHROPIC_OVERLOADED: {
    title: "Service temporarily overloaded",
    body:
      "The extraction service is at capacity. Your quota was refunded — try again shortly.",
  },
  ANTHROPIC_API: {
    title: "Couldn't reach the extraction service",
    body:
      "A network or upstream issue stopped us from completing this extraction. Your quota was refunded.",
  },
  MALFORMED_PDF: {
    title: "Couldn't read this document",
    body:
      "The extraction service couldn't process this file. Try a clearer scan, or a different page range.",
  },
  PARSE_ERROR: {
    title: "Couldn't parse the response",
    body:
      "The model returned data we couldn't decode. Try re-extracting this document.",
  },
  UNKNOWN: {
    title: "Something went wrong",
    body:
      "An unexpected error occurred. Your quota was refunded — try again, and contact support if it persists.",
  },
};

export function explainExtractionError(
  code: string | null | undefined,
  fallback: string | null | undefined,
): ExtractionErrorCopy {
  if (code && code in COPY) return COPY[code];
  return {
    title: "Extraction failed",
    body:
      fallback ??
      "This extraction returned no canonical data — likely a parse failure.",
  };
}
