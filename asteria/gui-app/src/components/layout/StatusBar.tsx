import {
  Wifi,
  WifiOff,
  Battery,
  BatteryLow,
  BatteryFull,
  BatteryMedium,
  Shield,
  Cpu,
  OctagonX,
  RefreshCw,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useStore } from "../../lib/store";
import { formatBattery, formatLease } from "../../lib/format";
import { Button } from "../ui/Button";
import { ThemeToggle } from "../ui/ThemeToggle";
import { playCue } from "../../lib/audio";

function ConnectionDot({ connected }: { connected: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {connected && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
      )}
      <span
        className={`relative inline-flex h-2.5 w-2.5 rounded-full ${connected ? "bg-success" : "bg-danger"}`}
      />
    </span>
  );
}

function BatteryIcon({ pct }: { pct?: number }) {
  if (pct == null || Number.isNaN(pct)) return <Battery size={14} className="text-tertiary" />;
  if (pct <= 20) return <BatteryLow size={14} className="text-danger" />;
  if (pct <= 50) return <BatteryMedium size={14} className="text-warning" />;
  return <BatteryFull size={14} className="text-success" />;
}

export function StatusBar() {
  const status = useStore((s) => s.status);
  const sendAction = useStore((s) => s.sendAction);
  const claimControl = useStore((s) => s.claimControl);
  const pollStatus = useStore((s) => s.pollStatus);
  const toggleSidebar = useStore((s) => s.toggleSidebar);
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed);
  const setCommandPaletteOpen = useStore((s) => s.setCommandPaletteOpen);

  const t = status.telemetry ?? ({} as NonNullable<typeof status.telemetry>);
  const lease = status.lease ?? {};
  const connected = !!t.connected;
  const batteryPct = t.battery_pct;
  const fsmName = t.running_fsm_name;

  return (
    <header className="flex items-center gap-1.5 h-12 px-3 bg-surface border-b border-border shrink-0 z-20">
      <button
        onClick={toggleSidebar}
        className="flex items-center justify-center w-8 h-8 rounded-lg text-secondary hover:text-primary hover:bg-surface-raised transition-colors mr-1 cursor-pointer"
        aria-label="Toggle sidebar"
      >
        {sidebarCollapsed ? (
          <PanelLeftOpen size={16} />
        ) : (
          <PanelLeftClose size={16} />
        )}
      </button>

      <div className="flex items-center gap-4 mr-auto overflow-hidden min-h-[32px] pl-1">
        {/* Connection */}
        <div className="flex items-center gap-2 text-xs whitespace-nowrap shrink-0">
          <ConnectionDot connected={connected} />
          <span className="text-secondary font-medium">
            {connected ? (
              <span className="flex items-center gap-1.5">
                <Wifi size={13} />
                {t.host ?? "Connected"}
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <WifiOff size={13} />
                Disconnected
              </span>
            )}
          </span>
        </div>

        {/* Battery */}
        <div className="flex items-center gap-1.5 text-xs text-secondary whitespace-nowrap shrink-0">
          <BatteryIcon pct={batteryPct} />
          <span className="font-medium min-w-[3ch] text-right">{formatBattery(batteryPct)}</span>
        </div>

        {/* FSM */}
        <div className="flex items-center gap-1.5 text-xs text-secondary whitespace-nowrap shrink-0">
          <Cpu size={13} />
          <span className="font-medium">
            {fsmName
              ? `${fsmName}${t.running_fsm_active ? "" : " (paused)"}`
              : "No FSM"}
          </span>
        </div>

        {/* Lease */}
        <div className="flex items-center gap-1.5 text-xs text-secondary whitespace-nowrap shrink-0">
          <Shield size={13} />
          <span className="font-medium min-w-[5ch]">{formatLease(lease)}</span>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="hidden sm:flex items-center gap-2 h-7 px-2.5 text-xs text-tertiary bg-surface-raised border border-border rounded-lg hover:text-secondary transition-colors cursor-pointer"
        >
          <span>Search actions</span>
          <kbd className="text-[10px] text-tertiary bg-bg px-1.5 py-0.5 rounded font-mono border border-border">
            ⌘K
          </kbd>
        </button>

        <Button
          size="sm"
          variant="primary"
          onClick={async () => {
            await claimControl({ force: true, refresh: true });
            playCue("success");
          }}
        >
          <Shield size={13} />
          Claim
        </Button>

        <Button
          size="sm"
          variant="ghost"
          onClick={() => { pollStatus(); playCue("click"); }}
          aria-label="Refresh"
        >
          <RefreshCw size={14} />
        </Button>

        <Button
          size="sm"
          variant="danger"
          onClick={async () => {
            await claimControl({ force: true, refresh: false });
            sendAction("stop_all", { stop_fsm: true });
          }}
        >
          <OctagonX size={14} />
          Stop
        </Button>

        <div className="w-px h-5 bg-border mx-1" />
        <ThemeToggle />
      </div>
    </header>
  );
}
