import { useState } from "react";
import { Wifi, WifiOff, Search, RotateCw, Save, XCircle, Unplug, ShieldOff } from "lucide-react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { MetricBox } from "../ui/MetricBox";

export function ConnectionCard() {
  const status = useStore((s) => s.status);
  const sendAction = useStore((s) => s.sendAction);
  const releaseLease = useStore((s) => s.releaseLease);
  const conn = status.connection ?? {};
  const t = status.telemetry ?? ({} as NonNullable<typeof status.telemetry>);
  const connected = !!t.connected;

  const [robotTarget, setRobotTarget] = useState("");
  const [fallbacks, setFallbacks] = useState("");

  const profiles = conn.profiles ?? [];
  const [selectedProfile, setSelectedProfile] = useState(
    conn.active_profile ?? "",
  );

  const displayedTarget =
    robotTarget || conn.override_target_input || "";
  const displayedFallbacks =
    fallbacks || (conn.fallback_hosts ?? []).join(", ");

  function parseFallbacks() {
    return displayedFallbacks
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Connection</Eyebrow>
          <CardTitle>Robot session</CardTitle>
        </div>
        <Badge variant={connected ? "success" : "danger"}>
          {connected ? (
            <span className="flex items-center gap-1.5">
              <Wifi size={11} /> Connected
            </span>
          ) : (
            <span className="flex items-center gap-1.5">
              <WifiOff size={11} /> Disconnected
            </span>
          )}
        </Badge>
      </CardHeader>

      <div className="grid grid-cols-2 gap-2 mb-4">
        <MetricBox
          label="Profile target"
          value={
            conn.profile_robot_id
              ? `${conn.profile_robot_id} (${conn.profile_robot_host ?? "n/a"})`
              : conn.profile_robot_host ?? "n/a"
          }
        />
        <MetricBox
          label="Resolved target"
          value={conn.resolved_host ?? "n/a"}
        />
        <MetricBox label="Source" value={conn.target_source ?? "n/a"} />
        <MetricBox
          label="Fallbacks"
          value={
            (conn.fallback_hosts ?? []).length
              ? (conn.fallback_hosts ?? []).join(", ")
              : "192.168.4.1 only"
          }
        />
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-secondary mb-1.5">
            Active profile
          </label>
          <select
            value={selectedProfile}
            onChange={(e) => setSelectedProfile(e.target.value)}
            className="w-full h-9 px-3 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
          >
            {profiles.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-secondary mb-1.5">
            Robot target / ID
          </label>
          <input
            type="text"
            value={displayedTarget}
            onChange={(e) => setRobotTarget(e.target.value)}
            placeholder="AIM-526BA018 or 10.0.0.114"
            className="w-full h-9 px-3 text-sm bg-surface-raised border border-border rounded-lg text-primary placeholder:text-tertiary outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-secondary mb-1.5">
            Fallback hosts
          </label>
          <input
            type="text"
            value={displayedFallbacks}
            onChange={(e) => setFallbacks(e.target.value)}
            placeholder="comma-separated fallbacks"
            className="w-full h-9 px-3 text-sm bg-surface-raised border border-border rounded-lg text-primary placeholder:text-tertiary outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mt-4">
        <Button
          variant="primary"
          size="sm"
          onClick={() =>
            sendAction(
              "set_connection_config",
              {
                profile: selectedProfile,
                robot_target: displayedTarget,
                fallback_hosts: parseFallbacks(),
              },
              { leaseRequired: false },
            )
          }
        >
          Apply Target
        </Button>
        <Button
          size="sm"
          onClick={() =>
            sendAction(
              "save_profile_robot_target",
              { profile: selectedProfile, robot_target: displayedTarget },
              { leaseRequired: false },
            )
          }
        >
          <Save size={13} /> Save
        </Button>
        <Button
          size="sm"
          onClick={() =>
            sendAction(
              "set_connection_config",
              {
                profile: selectedProfile,
                clear_override: true,
                fallback_hosts: parseFallbacks(),
              },
              { leaseRequired: false },
            )
          }
        >
          <XCircle size={13} /> Clear
        </Button>
        <Button
          size="sm"
          onClick={() =>
            sendAction("connect", {}, { leaseRequired: false })
          }
        >
          <Wifi size={13} /> Connect
        </Button>
        <Button
          size="sm"
          onClick={() =>
            sendAction("reconnect", {}, { leaseRequired: false })
          }
        >
          <RotateCw size={13} /> Reconnect
        </Button>
        <Button
          size="sm"
          onClick={() =>
            sendAction(
              "diagnose_connection",
              { host: displayedTarget },
              { leaseRequired: false },
            )
          }
        >
          <Search size={13} /> Diagnose
        </Button>
        <Button
          size="sm"
          variant="danger-ghost"
          onClick={() =>
            sendAction("disconnect", {}, { leaseRequired: false })
          }
        >
          <Unplug size={13} /> Disconnect
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => releaseLease()}
        >
          <ShieldOff size={13} /> Release Lease
        </Button>
      </div>

      <p className="mt-3 text-[11px] text-tertiary leading-relaxed">
        Accepts short AIM IDs, full AIM hostnames, campus wifi hostnames,
        or direct IPs.
      </p>
    </Card>
  );
}
