import { useState, useCallback, useEffect, useRef } from "react";
import { Send, Mic } from "lucide-react";
import { useStore } from "../../lib/store";
import { FsmToolbar } from "../fsm/FsmToolbar";
import { FsmBrowser } from "../fsm/FsmBrowser";
import { FsmCodeEditor } from "../fsm/FsmEditor";
import { FsmSummary } from "../fsm/FsmSummary";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { playCue } from "../../lib/audio";

function defaultFsmSource(name: string): string {
  const clean = (name || "asteria_demo").trim() || "asteria_demo";
  const cls =
    clean
      .split(/[^A-Za-z0-9]+/)
      .filter(Boolean)
      .map((p) => p[0].toUpperCase() + p.slice(1))
      .join("") || "AsteriaDemo";
  return `from aim_fsm import *\n\n\nclass ${cls}(StateMachineProgram):\n $setup{\n Say("${clean} ready") =C=> Forward(120) =C=> Turn(90) =C=> Say("${clean} complete")\n }\n`;
}

export function FsmView() {
  const status = useStore((s) => s.status);
  const sendAction = useStore((s) => s.sendAction);
  const selectedFsm = useStore((s) => s.selectedFsm);
  const setSelectedFsm = useStore((s) => s.setSelectedFsm);
  const editorDirty = useStore((s) => s.editorDirty);
  const setEditorDirty = useStore((s) => s.setEditorDirty);

  const files = status.fsm_files ?? [];
  const selected = files.find((f) => f.name === selectedFsm) ?? files[0];

  const [fsmName, setFsmName] = useState(
    selected?.name ?? selectedFsm ?? "asteria_demo",
  );
  const [editorContent, setEditorContent] = useState(
    selected?.content ?? defaultFsmSource(fsmName),
  );
  const [eventInput, setEventInput] = useState("");

  // Track which FSM we last loaded into the editor so we know when to sync.
  const loadedFsmRef = useRef<string | null>(selected?.name ?? null);
  // Suppresses the dirty flag when the editor change comes from a
  // programmatic content sync rather than the user typing.
  const suppressDirtyRef = useRef(false);

  useEffect(() => {
    const resolvedName = selected?.name ?? null;
    if (resolvedName && resolvedName !== loadedFsmRef.current) {
      loadedFsmRef.current = resolvedName;
      suppressDirtyRef.current = true;
      setFsmName(resolvedName);
      setEditorContent(selected?.content ?? defaultFsmSource(resolvedName));
      setEditorDirty(false);
    }
  }, [selected?.name, selected?.content, setEditorDirty]);

  const normalizeName = (raw: string) =>
    raw
      .replace(/[^A-Za-z0-9_]+/g, "_")
      .replace(/^_+|_+$/g, "") || "asteria_demo";

  const handleEditorChange = useCallback(
    (val: string) => {
      setEditorContent(val);
      if (suppressDirtyRef.current) {
        suppressDirtyRef.current = false;
        return;
      }
      if (!editorDirty) setEditorDirty(true);
    },
    [editorDirty, setEditorDirty],
  );

  async function save() {
    const name = normalizeName(fsmName);
    setFsmName(name);
    const res = await sendAction("create_fsm", {
      name,
      content: editorContent,
    });
    setEditorDirty(false);
    if (res?.name) setSelectedFsm(res.name as string);
  }

  async function compile() {
    await save();
    const name = normalizeName(fsmName);
    await sendAction("compile_fsm", { name });
  }

  async function run() {
    await compile();
    const name = normalizeName(fsmName);
    await sendAction("run_fsm", { module: name });
  }

  return (
    <div className="space-y-4 max-w-6xl">
      <FsmToolbar
        fsmName={fsmName}
        onNameChange={setFsmName}
        onNewTemplate={() => {
          setSelectedFsm(null);
          setEditorContent(defaultFsmSource(fsmName));
          setEditorDirty(true);
          playCue("click");
        }}
        onSave={save}
        onCompile={compile}
        onRun={run}
        onUnload={() => sendAction("unload_fsm")}
      />

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-3">
          <FsmBrowser />
        </div>
        <div className="col-span-12 lg:col-span-6">
          <Card>
            <CardHeader>
              <div>
                <Eyebrow>Editor</Eyebrow>
                <CardTitle>State machine source</CardTitle>
              </div>
              <Badge variant={editorDirty ? "warning" : "default"}>
                {editorDirty
                  ? "Draft changed"
                  : selected?.generated_exists
                    ? "Compiled"
                    : "Source only"}
              </Badge>
            </CardHeader>
            <FsmCodeEditor
              value={editorContent}
              onChange={handleEditorChange}
            />
          </Card>
        </div>
        <div className="col-span-12 lg:col-span-3">
          <FsmSummary />
        </div>
      </div>

      <Card>
        <CardHeader>
          <div>
            <Eyebrow>Inject event</Eyebrow>
            <CardTitle>Text + speech lane</CardTitle>
          </div>
        </CardHeader>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={eventInput}
            onChange={(e) => setEventInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && eventInput.trim()) {
                sendAction("send_text", { message: eventInput.trim() });
              }
            }}
            placeholder="Event payload for the active FSM"
            className="flex-1 min-w-0 h-9 px-3 text-sm bg-surface-raised border border-border rounded-lg text-primary placeholder:text-tertiary outline-none focus:ring-2 focus:ring-accent/30"
          />
          <div className="flex gap-2 shrink-0">
            <Button
              variant="primary"
              size="sm"
              className="flex-1 sm:flex-none"
              onClick={() => {
                if (eventInput.trim())
                  sendAction("send_text", { message: eventInput.trim() });
              }}
            >
              <Send size={13} /> Text
            </Button>
            <Button
              size="sm"
              className="flex-1 sm:flex-none"
              onClick={() => {
                if (eventInput.trim())
                  sendAction("send_speech", { message: eventInput.trim() });
              }}
            >
              <Mic size={13} /> Speech
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
