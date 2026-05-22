/**
 * Settings. Placeholder for step 3; full settings (profile, org,
 * members, billing, data & privacy) land alongside auth in step 5.
 */
export default function SettingsPage() {
  return (
    <main className="px-10 py-8 pb-20 w-full max-w-[1480px]">
      <h1 className="font-serif text-3xl leading-tight tracking-[-0.02em] font-normal m-0 mb-2.5">
        <em className="italic text-accent not-italic font-normal">Settings</em>
      </h1>
      <p className="text-[14.5px] text-ink-3 max-w-[560px] m-0">
        Account, organization, billing, data & privacy. Lands alongside auth in
        step 5 of Phase 4.
      </p>
    </main>
  );
}
