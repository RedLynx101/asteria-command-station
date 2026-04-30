import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { MetricBox } from "../ui/MetricBox";
import { formatPose } from "../../lib/format";

export function MetricsStrip() {
  const status = useStore((s) => s.status);
  const t = status.telemetry ?? ({} as NonNullable<typeof status.telemetry>);
  const conn = status.connection ?? {};
  const sl = status.safe_limits;

  const metrics: [string, string, "" | "success" | "warning" | "danger"][] = [
    ["Connected", t.connected ? "Yes" : "No", t.connected ? "success" : "warning"],
    ["Runtime mode", conn.connected_runtime_mode ?? "idle", ""],
    ["Pose", formatPose(t.pose), ""],
    [
      "FSM support",
      conn.supports_fsm_runtime === false ? "Disabled" : "Available",
      conn.supports_fsm_runtime === false ? "danger" : "",
    ],
    [
      "Safe move",
      sl?.max_move_mm != null ? `${sl.max_move_mm} mm` : "n/a",
      "",
    ],
    [
      "Safe turn",
      sl?.max_turn_deg != null ? `${sl.max_turn_deg}°` : "n/a",
      "",
    ],
  ];

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Status</Eyebrow>
          <CardTitle>Runtime metrics</CardTitle>
        </div>
      </CardHeader>
      <div className="grid grid-cols-3 gap-2">
        {metrics.map(([label, value, severity]) => (
          <MetricBox key={label} label={label} value={value} severity={severity} />
        ))}
      </div>
    </Card>
  );
}
