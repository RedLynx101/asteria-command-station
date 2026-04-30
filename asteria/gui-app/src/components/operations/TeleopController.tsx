import { useRef, useCallback, useState } from "react";
import {
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  OctagonX,
  ArrowLeftRight,
  Zap,
  Camera,
  Type,
} from "lucide-react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

function DpadButton({
  icon: Icon,
  label,
  action,
  isDanger,
  onAction,
  onHoldStart,
  onHoldEnd,
  continuousMode,
}: {
  icon: typeof ChevronUp;
  label: string;
  action: string;
  isDanger?: boolean;
  onAction: (action: string) => void;
  onHoldStart?: (action: string) => void;
  onHoldEnd?: () => void;
  continuousMode: boolean;
}) {
  const [active, setActive] = useState(false);

  return (
    <button
      className={`flex items-center justify-center w-14 h-14 rounded-2xl border text-lg font-bold transition-all duration-100 cursor-pointer select-none
        ${
          isDanger
            ? "bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 active:bg-danger/30"
            : active
              ? "bg-accent/20 border-accent/40 text-accent shadow-[0_0_16px_rgba(34,211,238,0.2)]"
              : "bg-surface-raised border-border text-accent hover:bg-accent/10 hover:border-accent/30 active:bg-accent/20"
        }`}
      aria-label={label}
      onPointerDown={(e) => {
        if (continuousMode && onHoldStart && !isDanger) {
          e.preventDefault();
          setActive(true);
          (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          onHoldStart(action);
        }
      }}
      onPointerUp={() => {
        if (active) {
          setActive(false);
          onHoldEnd?.();
        }
      }}
      onPointerCancel={() => {
        if (active) {
          setActive(false);
          onHoldEnd?.();
        }
      }}
      onClick={() => {
        if (!continuousMode || isDanger) {
          onAction(action);
        }
      }}
    >
      <Icon size={22} />
    </button>
  );
}

export function TeleopController() {
  const sendAction = useStore((s) => s.sendAction);
  const continuousDirectControl = useStore((s) => s.continuousDirectControl);
  const setContinuousDirectControl = useStore(
    (s) => s.setContinuousDirectControl,
  );

  const [moveMm, setMoveMm] = useState(120);
  const [strafeMm, setStrafeMm] = useState(120);
  const [turnDeg, setTurnDeg] = useState(90);
  const [sayText, setSayText] = useState("Asteria online");

  const holdRef = useRef(false);

  const continuousPayload = useCallback(
    (action: string) => {
      const map: Record<string, { a: string; p: Record<string, unknown> }> = {
        moveForward: { a: "drive_at", p: { angle_deg: 0, speed_pct: 55 } },
        moveBackward: {
          a: "drive_at",
          p: { angle_deg: 180, speed_pct: 55 },
        },
        strafeLeft: { a: "drive_at", p: { angle_deg: -90, speed_pct: 52 } },
        strafeRight: { a: "drive_at", p: { angle_deg: 90, speed_pct: 52 } },
        turnLeft: { a: "turn_at", p: { turn_rate_pct: -40 } },
        turnRight: { a: "turn_at", p: { turn_rate_pct: 40 } },
      };
      return map[action];
    },
    [],
  );

  const discreteAction = useCallback(
    async (action: string) => {
      const map: Record<
        string,
        { a: string; p: Record<string, unknown> }
      > = {
        moveForward: {
          a: "move",
          p: { distance_mm: moveMm, angle_deg: 0 },
        },
        moveBackward: {
          a: "move",
          p: { distance_mm: -moveMm, angle_deg: 0 },
        },
        strafeLeft: { a: "sideways", p: { distance_mm: -strafeMm } },
        strafeRight: { a: "sideways", p: { distance_mm: strafeMm } },
        turnLeft: { a: "turn", p: { angle_deg: -turnDeg } },
        turnRight: { a: "turn", p: { angle_deg: turnDeg } },
        stopAll: { a: "stop_all", p: { stop_fsm: true } },
      };
      const entry = map[action];
      if (entry) await sendAction(entry.a, entry.p);
    },
    [sendAction, moveMm, strafeMm, turnDeg],
  );

  const startHold = useCallback(
    async (action: string) => {
      holdRef.current = true;
      const cp = continuousPayload(action);
      if (cp) await sendAction(cp.a, cp.p);
    },
    [sendAction, continuousPayload],
  );

  const endHold = useCallback(async () => {
    if (!holdRef.current) return;
    holdRef.current = false;
    await sendAction("stop_all", { stop_fsm: false });
  }, [sendAction]);

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Direct control</Eyebrow>
          <CardTitle>Motion + actions</CardTitle>
        </div>
        <Badge variant="accent">Lease-gated</Badge>
      </CardHeader>

      <div className="flex gap-6 mb-4">
        {/* D-pad */}
        <div className="grid grid-cols-3 grid-rows-3 gap-2 shrink-0">
          <div />
          <DpadButton
            icon={ChevronUp}
            label="Forward"
            action="moveForward"
            onAction={discreteAction}
            onHoldStart={startHold}
            onHoldEnd={endHold}
            continuousMode={continuousDirectControl}
          />
          <div />
          <DpadButton
            icon={ChevronLeft}
            label="Turn left"
            action="turnLeft"
            onAction={discreteAction}
            onHoldStart={startHold}
            onHoldEnd={endHold}
            continuousMode={continuousDirectControl}
          />
          <DpadButton
            icon={OctagonX}
            label="Stop"
            action="stopAll"
            isDanger
            onAction={discreteAction}
            onHoldStart={startHold}
            onHoldEnd={endHold}
            continuousMode={continuousDirectControl}
          />
          <DpadButton
            icon={ChevronRight}
            label="Turn right"
            action="turnRight"
            onAction={discreteAction}
            onHoldStart={startHold}
            onHoldEnd={endHold}
            continuousMode={continuousDirectControl}
          />
          <div />
          <DpadButton
            icon={ChevronDown}
            label="Backward"
            action="moveBackward"
            onAction={discreteAction}
            onHoldStart={startHold}
            onHoldEnd={endHold}
            continuousMode={continuousDirectControl}
          />
          <div />
        </div>

        {/* Action grid */}
        <div className="grid grid-cols-2 gap-2 flex-1 content-start">
          <Button
            size="sm"
            onClick={() => discreteAction("strafeLeft")}
          >
            <ArrowLeftRight size={13} /> Strafe L
          </Button>
          <Button
            size="sm"
            onClick={() => discreteAction("strafeRight")}
          >
            <ArrowLeftRight size={13} /> Strafe R
          </Button>
          <Button
            size="sm"
            onClick={() => sendAction("kick", { style: "soft" })}
          >
            <Zap size={13} /> Soft
          </Button>
          <Button
            size="sm"
            onClick={() => sendAction("kick", { style: "medium" })}
          >
            <Zap size={13} /> Medium
          </Button>
          <Button
            size="sm"
            onClick={() => sendAction("kick", { style: "hard" })}
          >
            <Zap size={13} /> Hard
          </Button>
          <Button
            size="sm"
            onClick={() =>
              sendAction("capture_image", {}, { refreshAfter: true })
            }
          >
            <Camera size={13} /> Capture
          </Button>
        </div>
      </div>

      {/* Continuous toggle */}
      <label className="flex items-center gap-3 p-3 bg-surface-raised border border-border rounded-lg cursor-pointer mb-4">
        <input
          type="checkbox"
          checked={continuousDirectControl}
          onChange={(e) => setContinuousDirectControl(e.target.checked)}
          className="w-4 h-4 accent-accent shrink-0"
        />
        <div>
          <span className="text-sm font-medium text-primary block">
            Continuous hold mode
          </span>
          <span className="text-[11px] text-tertiary">
            Hold buttons to drive live. Release stops motion.
          </span>
        </div>
      </label>

      {/* Step controls */}
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div>
          <label className="block text-[11px] font-medium text-secondary mb-1">
            Move mm
          </label>
          <input
            type="number"
            value={moveMm}
            onChange={(e) => setMoveMm(Number(e.target.value))}
            className="w-full h-8 px-2.5 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-[11px] font-medium text-secondary mb-1">
            Strafe mm
          </label>
          <input
            type="number"
            value={strafeMm}
            onChange={(e) => setStrafeMm(Number(e.target.value))}
            className="w-full h-8 px-2.5 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-[11px] font-medium text-secondary mb-1">
            Turn deg
          </label>
          <input
            type="number"
            value={turnDeg}
            onChange={(e) => setTurnDeg(Number(e.target.value))}
            className="w-full h-8 px-2.5 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
      </div>

      {/* Say text */}
      <div className="flex gap-2">
        <input
          type="text"
          value={sayText}
          onChange={(e) => setSayText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") sendAction("say", { text: sayText });
          }}
          placeholder="Screen text"
          className="flex-1 h-9 px-3 text-sm bg-surface-raised border border-border rounded-lg text-primary placeholder:text-tertiary outline-none focus:ring-2 focus:ring-accent/30"
        />
        <Button
          size="sm"
          onClick={() => sendAction("say", { text: sayText })}
        >
          <Type size={13} /> Display
        </Button>
      </div>
    </Card>
  );
}
