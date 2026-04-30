import { FilePlus, Save, Hammer, Play, Trash2 } from "lucide-react";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";

interface FsmToolbarProps {
  fsmName: string;
  onNameChange: (name: string) => void;
  onNewTemplate: () => void;
  onSave: () => void;
  onCompile: () => void;
  onRun: () => void;
  onUnload: () => void;
}

export function FsmToolbar({
  fsmName,
  onNameChange,
  onNewTemplate,
  onSave,
  onCompile,
  onRun,
  onUnload,
}: FsmToolbarProps) {
  return (
    <Card className="flex flex-wrap items-center gap-3">
      <div className="flex-1 min-w-[200px]">
        <label className="block text-[11px] font-medium text-secondary mb-1">
          FSM name
        </label>
        <input
          type="text"
          value={fsmName}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="asteria_demo"
          className="w-full h-8 px-2.5 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
        />
      </div>
      <div className="flex flex-wrap gap-2 items-end">
        <Button size="sm" onClick={onNewTemplate}>
          <FilePlus size={13} /> New
        </Button>
        <Button size="sm" variant="primary" onClick={onSave}>
          <Save size={13} /> Save
        </Button>
        <Button size="sm" onClick={onCompile}>
          <Hammer size={13} /> Compile
        </Button>
        <Button size="sm" onClick={onRun}>
          <Play size={13} /> Run
        </Button>
        <Button size="sm" variant="danger-ghost" onClick={onUnload}>
          <Trash2 size={13} /> Unload
        </Button>
      </div>
    </Card>
  );
}
