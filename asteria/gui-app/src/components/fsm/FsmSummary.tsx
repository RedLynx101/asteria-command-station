import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { MetricBox } from "../ui/MetricBox";

function compactPath(pathValue: string | undefined, repoRoot?: string): string {
  if (!pathValue) return "n/a";
  const norm = pathValue.replace(/\\/g, "/");
  if (repoRoot) {
    const prefix = `${repoRoot.replace(/\\/g, "/")}/`;
    if (norm.toLowerCase().startsWith(prefix.toLowerCase()))
      return norm.slice(prefix.length);
  }
  const segs = norm.split("/").filter(Boolean);
  return segs.length ? segs.slice(-3).join("/") : norm;
}

export function FsmSummary() {
  const status = useStore((s) => s.status);
  const selectedFsm = useStore((s) => s.selectedFsm);
  const files = status.fsm_files ?? [];
  const selected = files.find((f) => f.name === selectedFsm) ?? files[0];
  const t = status.telemetry ?? ({} as NonNullable<typeof status.telemetry>);

  return (
    <Card className="h-full">
      <CardHeader>
        <div>
          <Eyebrow>Runtime</Eyebrow>
          <CardTitle>FSM summary</CardTitle>
        </div>
      </CardHeader>
      <div className="grid grid-cols-1 gap-2">
        <MetricBox
          label="Selected FSM"
          value={selected?.name ?? "n/a"}
        />
        <MetricBox
          label="Generated file"
          value={compactPath(selected?.generated_py, status.paths?.repo_root)}
        />
        <MetricBox
          label="Compiled"
          value={selected?.generated_exists ? "Yes" : "No"}
          severity={selected?.generated_exists ? "success" : ""}
        />
        <MetricBox
          label="Runtime state"
          value={
            t.running_fsm_name
              ? t.running_fsm_active
                ? "Running"
                : "Loaded"
              : "Idle"
          }
          severity={t.running_fsm_active ? "success" : ""}
        />
      </div>
    </Card>
  );
}
