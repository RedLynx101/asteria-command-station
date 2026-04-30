import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { formatTimestamp } from "../../lib/format";

export function ResultCard() {
  const status = useStore((s) => s.status);
  const lr = status.last_result ?? {};
  const image = status.latest_image ?? {};

  let kind: "default" | "success" | "warning" | "danger" = "default";
  if (lr.warning) kind = "warning";
  else if (lr.ok === true) kind = "success";
  else if (lr.ok === false) kind = "danger";

  const details: string[] = [];
  if (lr.error) details.push(lr.error);
  else details.push(lr.message ?? "Commands, safety notices, and generated file links will appear here.");
  if (lr.warning) details.push(lr.warning);
  if (lr.generated_exists === true) details.push("Generated Python is available.");
  if (lr.generated_exists === false) details.push("FSM source exists but has not been compiled yet.");
  if (image.captured_at) details.push(`Latest image: ${formatTimestamp(image.captured_at)}.`);

  const bgStyles: Record<string, string> = {
    default: "bg-surface-raised border-border",
    success: "bg-success-soft border-success/20",
    warning: "bg-warning-soft border-warning/20",
    danger: "bg-danger-soft border-danger/20",
  };

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Latest result</Eyebrow>
          <CardTitle>Command feedback</CardTitle>
        </div>
        <Badge variant={kind === "default" ? "default" : kind}>
          {kind.toUpperCase()}
        </Badge>
      </CardHeader>
      <div className={`border rounded-lg p-3 ${bgStyles[kind]}`}>
        <strong className="text-sm font-semibold text-primary block mb-1">
          {lr.message ?? lr.error ?? "No recent action"}
        </strong>
        <p className="text-xs text-secondary leading-relaxed">
          {details.join(" ")}
        </p>
      </div>
    </Card>
  );
}
