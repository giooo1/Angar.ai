import { explainExtractionError } from "@/lib/extraction-errors";

type Props = {
  errorCode: string | null;
  errorMessage: string | null;
};

/**
 * Renders an extraction failure in the right pane of the review screen.
 *
 * Reads `error_code` (populated by the backend's typed-exception
 * dispatch) and renders a friendly, code-specific message. Falls back
 * to `error_message` if the code is unknown or null.
 */
export function ExtractionErrorCard({ errorCode, errorMessage }: Props) {
  const copy = explainExtractionError(errorCode, errorMessage);

  return (
    <div className="bg-paper border border-line rounded-xl p-6">
      <p className="font-serif text-[17px] font-medium text-ink m-0 mb-2">
        {copy.title}
      </p>
      <p className="m-0 text-[13px] text-ink-3 leading-relaxed">{copy.body}</p>
      {errorCode && (
        <p className="m-0 mt-3 font-mono text-[10.5px] text-ink-4 tracking-[0.04em]">
          {errorCode}
        </p>
      )}
    </div>
  );
}
