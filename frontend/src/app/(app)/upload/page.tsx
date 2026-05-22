/**
 * Upload screen — file drag-drop + recent uploads + usage panel.
 * Step 3 of Phase 4. This file currently renders a stub heading;
 * the real UI lands when the upload components are written.
 */
export default function UploadPage() {
  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      <h1 className="font-serif text-3xl leading-tight tracking-[-0.02em] font-normal m-0 mb-2.5">
        Upload <em className="italic text-accent not-italic font-normal">documents</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0">
        Drop PDF, JPG, PNG, or HEIC files. Each one runs through Claude vision
        and lands in your review queue.
      </p>
      <div className="mt-8 p-12 bg-paper border-2 border-dashed border-line rounded-xl text-center text-ink-3 text-sm">
        Drop zone — real component lands in the next commit.
      </div>
    </main>
  );
}
