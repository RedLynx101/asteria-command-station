import { useStore } from "../../lib/store";
import { Badge } from "../ui/Badge";
import { formatTimestamp } from "../../lib/format";

export function StatusBanner() {
  const status = useStore((s) => s.status);
  const t = status.telemetry ?? ({} as NonNullable<typeof status.telemetry>);
  const conn = status.connection ?? {};
  const lr = status.last_result ?? {};
  const lease = status.lease ?? {};
  const image = status.latest_image ?? {};

  let title = "Ready for operator input";
  let body = "Asteria is waiting for the next daemon status refresh.";
  let variant: "default" | "success" | "warning" | "danger" = "default";

  if (lr.error) {
    title = "Recent action needs attention";
    body = lr.error;
    variant = "danger";
  } else if (lr.message) {
    title = lr.message;
    body = t.connected
      ? `Robot session active on ${t.host ?? conn.resolved_host ?? "the selected host"}.`
      : "Daemon reachable, robot not connected.";
    variant = t.connected ? "success" : "warning";
  } else if (t.connected) {
    title = "Robot ready for operator input";
    body = `Connected to ${t.host ?? conn.resolved_host ?? "the selected host"} with ${conn.connected_runtime_mode ?? "current"} runtime mode.`;
    variant = "success";
  }

  const tags: string[] = [];
  tags.push(conn.active_profile ? `Profile: ${conn.active_profile}` : "Profile: n/a");
  tags.push(lease.holder_id ? `Lease: ${lease.holder_label ?? lease.holder_id}` : "Lease: unclaimed");
  if (conn.supports_fsm_runtime === false) tags.push("FSM runtime unavailable");
  if (image.captured_at) tags.push(`Image: ${formatTimestamp(image.captured_at)}`);

  const bannerBg: Record<string, string> = {
    default: "bg-surface border-border",
    success: "bg-success-soft border-success/20",
    warning: "bg-warning-soft border-warning/20",
    danger: "bg-danger-soft border-danger/20",
  };

  return (
    <div className={`border rounded-xl p-4 ${bannerBg[variant]}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-primary">{title}</h2>
          <p className="text-sm text-secondary mt-0.5">{body}</p>
        </div>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {tags.map((tag) => (
            <Badge key={tag} variant="accent">
              {tag}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
