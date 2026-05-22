/**
 * Review queue. Placeholder for step 3; the side-by-side PDF + extracted
 * data review experience lands in step 4 of Phase 4.
 */
export default function ReviewPage() {
  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      <h1 className="font-serif text-3xl leading-tight tracking-[-0.02em] font-normal m-0 mb-2.5">
        Review <em className="italic text-accent not-italic font-normal">queue</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0">
        Side-by-side document + extracted data view. Step 4 of Phase 4 builds
        this against the existing{" "}
        <code className="font-mono text-[13px]">GET /api/v1/extractions/{"{id}"}</code>{" "}
        endpoint.
      </p>
    </main>
  );
}
