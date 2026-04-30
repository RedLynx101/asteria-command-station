import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useStore } from "../../lib/store";
import { ImageViewer } from "../vision/ImageViewer";
import { TelemetryPanel } from "../vision/TelemetryPanel";
import { Card } from "../ui/Card";
import { MiniCard } from "../ui/MiniCard";
import { formatTimestamp } from "../../lib/format";

export function VisionView() {
  const status = useStore((s) => s.status);
  const [logOpen, setLogOpen] = useState(false);
  const commands = [...(status.recent_commands ?? [])].reverse();

  return (
    <div className="space-y-4 max-w-6xl">
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8">
          <ImageViewer />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <TelemetryPanel />
        </div>
      </div>

      <Card>
        <button
          onClick={() => setLogOpen(!logOpen)}
          className="flex items-center gap-2 w-full text-left text-sm font-bold text-primary cursor-pointer"
        >
          {logOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          Recent command log
        </button>
        {logOpen && (
          <div className="mt-3 space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {commands.length === 0 ? (
              <MiniCard
                title="No recent commands"
                body="Recent command traffic will appear here."
              />
            ) : (
              commands.map((cmd, i) => (
                <MiniCard
                  key={i}
                  title={cmd.action ?? "command"}
                  meta={formatTimestamp(cmd.timestamp)}
                  body={JSON.stringify(cmd.payload ?? {}, null, 2)}
                />
              ))
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
