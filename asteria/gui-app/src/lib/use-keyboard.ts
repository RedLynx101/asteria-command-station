import { useEffect } from "react";
import { useStore } from "./store";
import type { View } from "./types";
import { VIEWS } from "./constants";

const INPUT_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isTyping(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  if (INPUT_TAGS.has(el.tagName)) return true;
  if ((el as HTMLElement).isContentEditable) return true;
  if (el.closest(".cm-editor")) return true;
  return false;
}

export function useKeyboardShortcuts() {
  const setView = useStore((s) => s.setView);
  const setCommandPaletteOpen = useStore((s) => s.setCommandPaletteOpen);
  const setShortcutsOpen = useStore((s) => s.setShortcutsOpen);
  const sendAction = useStore((s) => s.sendAction);
  const claimControl = useStore((s) => s.claimControl);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;

      if (meta && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(true);
        return;
      }

      if (isTyping()) return;

      if (e.key === "?") {
        e.preventDefault();
        setShortcutsOpen(true);
        return;
      }

      const digit = parseInt(e.key, 10);
      if (digit >= 1 && digit <= 5) {
        e.preventDefault();
        setView(VIEWS[digit - 1] as View);
        return;
      }

      if (e.key === "Escape") {
        setCommandPaletteOpen(false);
        setShortcutsOpen(false);
        return;
      }

      if (e.key === " ") {
        e.preventDefault();
        claimControl({ force: true, refresh: false }).then(() =>
          sendAction("stop_all", { stop_fsm: true }),
        );
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setView, setCommandPaletteOpen, setShortcutsOpen, sendAction, claimControl]);
}
