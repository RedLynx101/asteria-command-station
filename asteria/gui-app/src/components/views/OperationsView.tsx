import { StatusBanner } from "../operations/StatusBanner";
import { ConnectionCard } from "../operations/ConnectionCard";
import { TeleopController } from "../operations/TeleopController";
import { MiniImagePreview } from "../operations/MiniImagePreview";
import { MetricsStrip } from "../operations/MetricsStrip";
import { ResultCard } from "../operations/ResultCard";

export function OperationsView() {
  return (
    <div className="space-y-4 max-w-6xl">
      <StatusBanner />
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-5">
          <ConnectionCard />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <TeleopController />
        </div>
        <div className="col-span-12 lg:col-span-3">
          <MiniImagePreview />
        </div>
      </div>
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-6">
          <MetricsStrip />
        </div>
        <div className="col-span-12 lg:col-span-6">
          <ResultCard />
        </div>
      </div>
    </div>
  );
}
