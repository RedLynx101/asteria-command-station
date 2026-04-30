import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";

export function StopPolicy() {
  const stopAllUnloadsFsm = useStore((s) => s.stopAllUnloadsFsm);
  const setStopAllUnloadsFsm = useStore((s) => s.setStopAllUnloadsFsm);
  const status = useStore((s) => s.status);
  const activeFsm = status.telemetry?.running_fsm_name;

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Stop policy</Eyebrow>
          <CardTitle>Emergency behavior</CardTitle>
        </div>
      </CardHeader>
      <label className="flex items-start gap-3 p-3 bg-surface-raised border border-border rounded-lg cursor-pointer">
        <input
          type="checkbox"
          checked={stopAllUnloadsFsm}
          onChange={(e) => setStopAllUnloadsFsm(e.target.checked)}
          className="w-4 h-4 mt-0.5 accent-accent shrink-0"
        />
        <div>
          <span className="text-sm font-medium text-primary block">
            Stop buttons unload the active FSM
          </span>
          <span className="text-[11px] text-tertiary leading-relaxed block mt-1">
            {stopAllUnloadsFsm
              ? "Stop All and the D-pad stop button will unload the current FSM before halting motion."
              : "Stop All and the D-pad stop button only halt motion. The active FSM stays loaded."}
            {activeFsm ? ` Active FSM: ${activeFsm}.` : ""}
          </span>
        </div>
      </label>
    </Card>
  );
}
