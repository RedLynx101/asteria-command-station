import { useStore } from "../../lib/store";
import { X } from "lucide-react";

const SHORTCUTS = [
  { keys: ["⌘", "K"], description: "Open command palette" },
  { keys: ["1"], description: "Operations view" },
  { keys: ["2"], description: "Desk view" },
  { keys: ["3"], description: "FSM view" },
  { keys: ["4"], description: "Vision view" },
  { keys: ["5"], description: "Debug view" },
  { keys: ["?"], description: "Show this panel" },
  { keys: ["Space"], description: "Emergency stop (when not typing)" },
  { keys: ["⌘", "Enter"], description: "Send prompt (in desk)" },
  { keys: ["Esc"], description: "Close overlays" },
];

export function ShortcutsOverlay() {
  const open = useStore((s) => s.shortcutsOpen);
  const setOpen = useStore((s) => s.setShortcutsOpen);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />
      <div className="relative w-full max-w-md bg-surface border border-border rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-bold text-primary">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={() => setOpen(false)}
            className="flex items-center justify-center w-7 h-7 rounded-lg text-secondary hover:text-primary hover:bg-surface-raised transition-colors cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-3 space-y-1">
          {SHORTCUTS.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-surface-raised"
            >
              <span className="text-sm text-secondary">{s.description}</span>
              <div className="flex gap-1">
                {s.keys.map((k) => (
                  <kbd
                    key={k}
                    className="inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 text-[11px] font-mono font-semibold text-secondary bg-bg border border-border rounded"
                  >
                    {k}
                  </kbd>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
