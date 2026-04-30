import { useState } from "react";
import { Send, StickyNote } from "lucide-react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

type ForwardMode = "queue" | "openclaw" | "codex";

const FORWARD_MODE_OPTIONS: { value: ForwardMode; label: string }[] = [
  { value: "queue", label: "Queue only" },
  { value: "openclaw", label: "OpenClaw" },
  { value: "codex", label: "Codex" },
];

function readStoredMode(): ForwardMode {
  try {
    const v = localStorage.getItem("asteria.forwardMode");
    if (v === "queue" || v === "openclaw" || v === "codex") return v;
  } catch { /* noop */ }
  return "queue";
}

const DRAFT_KEY = "asteria.deskDraft";

function readDraft(): string {
  try { return localStorage.getItem(DRAFT_KEY) ?? ""; } catch { return ""; }
}

function writeDraft(v: string) {
  try { localStorage.setItem(DRAFT_KEY, v); } catch { /* noop */ }
}

function clearDraft() {
  try { localStorage.removeItem(DRAFT_KEY); } catch { /* noop */ }
}

export function PromptComposer() {
  const sendAction = useStore((s) => s.sendAction);
  const status = useStore((s) => s.status);
  const [text, setText] = useState(readDraft);
  const [forwardMode, setForwardMode] = useState<ForwardMode>(readStoredMode);

  const openCount = (status.prompts ?? []).filter(
    (p) => p.status !== "resolved",
  ).length;

  function changeMode(mode: ForwardMode) {
    setForwardMode(mode);
    try { localStorage.setItem("asteria.forwardMode", mode); } catch { /* noop */ }
  }

  function updateText(v: string) {
    setText(v);
    writeDraft(v);
  }

  function clearText() {
    setText("");
    clearDraft();
  }

  async function submitPrompt() {
    if (!text.trim()) return;
    await sendAction(
      "submit_prompt",
      { text: text.trim(), forward_mode: forwardMode },
      { leaseRequired: false },
    );
    clearText();
  }

  async function logNote() {
    if (!text.trim()) return;
    await sendAction(
      "log_note",
      { title: "Operator note", message: text.trim(), level: "info" },
      { leaseRequired: false },
    );
    clearText();
  }

  return (
    <Card className="w-full flex flex-col">
      <CardHeader>
        <div>
          <Eyebrow>Desk</Eyebrow>
          <CardTitle>Prompt + notes</CardTitle>
        </div>
        <Badge variant="accent">{openCount} open</Badge>
      </CardHeader>
      <div className="flex flex-col flex-1 gap-3">
        <div>
          <label className="block text-xs font-medium text-secondary mb-1.5">
            Forward mode
          </label>
          <select
            value={forwardMode}
            onChange={(e) => changeMode(e.target.value as ForwardMode)}
            className="w-full h-9 px-3 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
          >
            {FORWARD_MODE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <textarea
          value={text}
          onChange={(e) => updateText(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
              e.preventDefault();
              submitPrompt();
            }
          }}
          rows={5}
          placeholder="Ask Asteria to inspect, move, explain, or act..."
          className="w-full flex-1 min-h-[120px] px-3 py-2.5 text-sm bg-surface-raised border border-border rounded-lg text-primary placeholder:text-tertiary outline-none focus:ring-2 focus:ring-accent/30 resize-none leading-relaxed"
        />
        <div className="flex gap-2">
          <Button variant="primary" onClick={submitPrompt}>
            <Send size={14} /> Send Prompt
          </Button>
          <Button onClick={logNote}>
            <StickyNote size={14} /> Log Note
          </Button>
        </div>
        <p className="text-[10px] text-tertiary">
          <kbd className="font-mono bg-surface-raised px-1 py-0.5 rounded border border-border">⌘Enter</kbd> to
          send prompt
        </p>
      </div>
    </Card>
  );
}
