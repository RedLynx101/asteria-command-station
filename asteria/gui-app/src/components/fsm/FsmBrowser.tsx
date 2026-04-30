import { FileCode2 } from "lucide-react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { playCue } from "../../lib/audio";

export function FsmBrowser() {
  const status = useStore((s) => s.status);
  const selectedFsm = useStore((s) => s.selectedFsm);
  const setSelectedFsm = useStore((s) => s.setSelectedFsm);
  const files = status.fsm_files ?? [];

  return (
    <Card className="h-full">
      <CardHeader>
        <div>
          <Eyebrow>Files</Eyebrow>
          <CardTitle>FSM browser</CardTitle>
        </div>
      </CardHeader>
      <div className="space-y-1 max-h-[420px] overflow-y-auto pr-1">
        {files.length === 0 ? (
          <p className="text-xs text-tertiary py-2">No FSM files found.</p>
        ) : (
          files.map((f) => (
            <button
              key={f.name}
              onClick={() => {
                setSelectedFsm(f.name);
                playCue("click");
              }}
              className={`flex items-center gap-2 w-full px-2.5 py-2 text-sm rounded-lg text-left transition-colors cursor-pointer ${
                selectedFsm === f.name
                  ? "bg-accent-soft text-accent border border-accent/20"
                  : "text-secondary hover:bg-surface-raised hover:text-primary border border-transparent"
              }`}
            >
              <FileCode2 size={14} className="shrink-0" />
              <span className="truncate">{f.name}</span>
            </button>
          ))
        )}
      </div>
    </Card>
  );
}
