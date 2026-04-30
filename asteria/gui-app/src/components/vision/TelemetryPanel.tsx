import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { MetricBox } from "../ui/MetricBox";
import { formatBattery, formatPose, formatTimestamp } from "../../lib/format";

export function TelemetryPanel() {
  const status = useStore((s) => s.status);
  const t = status.telemetry ?? ({} as NonNullable<typeof status.telemetry>);
  const conn = status.connection ?? {};
  const image = status.latest_image ?? {};
  const lease = status.lease ?? {};

  const items: [string, string][] = [
    ["Battery", formatBattery(t.battery_pct)],
    ["Pose", formatPose(t.pose)],
    ["Host", t.host ?? conn.resolved_host ?? "n/a"],
    ["Lease", lease.holder_label ?? "Unclaimed"],
    ["Last capture", image.captured_at ? formatTimestamp(image.captured_at) : "n/a"],
    ["Last error", t.last_error ?? "None"],
  ];

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Telemetry</Eyebrow>
          <CardTitle>Snapshot</CardTitle>
        </div>
      </CardHeader>
      <div className="grid grid-cols-1 gap-2">
        {items.map(([label, value]) => (
          <MetricBox key={label} label={label} value={value} />
        ))}
      </div>
    </Card>
  );
}
