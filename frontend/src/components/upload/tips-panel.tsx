import { InfoIcon, ShieldCheckIcon } from "@/components/ui/icons";

/**
 * Right-column tips card. Static content, mostly explanatory. Lives
 * below the recent-uploads list so the eye lands on it after looking
 * at recent work.
 */
export function TipsPanel() {
  return (
    <div className="bg-paper border border-line rounded-xl p-[18px]">
      <h3 className="m-0 mb-3 font-serif text-[17px] font-medium tracking-[-0.015em]">
        Tips
      </h3>

      <div className="flex flex-col gap-2 text-[12.5px] text-ink-2 leading-[1.55]">
        <div className="flex gap-2 items-start">
          <ShieldCheckIcon size={14} strokeWidth={2} className="text-accent mt-0.5 flex-shrink-0" />
          <span>
            ატვირთულ ფაილებს ვინახავთ კონფიდენციალურად 30 დღის განმავლობაში.
            Pro გეგმაში — 1 წელი.
          </span>
        </div>
        <div className="flex gap-2 items-start">
          <InfoIcon size={14} strokeWidth={2} className="text-accent mt-0.5 flex-shrink-0" />
          <span>
            ფოტო ხარისხის სიზუსტეც გავიწევთ — უმჯობესია სუფთა PDF.
          </span>
        </div>
      </div>
    </div>
  );
}
