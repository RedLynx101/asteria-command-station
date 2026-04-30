import { PromptComposer } from "../desk/PromptComposer";
import { PromptQueue } from "../desk/PromptQueue";
import { ActivityTimeline } from "../desk/ActivityTimeline";

export function DeskView() {
  return (
    <div className="space-y-4 max-w-6xl">
      <div className="grid grid-cols-12 gap-4 items-stretch">
        <div className="col-span-12 lg:col-span-5 flex">
          <PromptComposer />
        </div>
        <div className="col-span-12 lg:col-span-7 flex">
          <PromptQueue />
        </div>
      </div>
      <ActivityTimeline />
    </div>
  );
}
