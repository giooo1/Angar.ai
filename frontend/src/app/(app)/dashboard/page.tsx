/**
 * Documents dashboard. Placeholder for step 3; real implementation
 * lands in step 7 once the backend exposes a documents-list endpoint.
 */
export default function DashboardPage() {
  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      <h1 className="font-serif text-3xl leading-tight tracking-[-0.02em] font-normal m-0 mb-2.5">
        Documents <em className="italic text-accent not-italic font-normal">library</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0">
        Searchable document history. Building this is step 7 of Phase 4 —
        depends on a new <code className="font-mono text-[13px]">GET /api/v1/documents</code>{" "}
        endpoint on the backend.
      </p>
    </main>
  );
}
