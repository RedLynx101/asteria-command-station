import { useStore } from "../../lib/store";
import { StopPolicy } from "../debug/StopPolicy";
import { CodexSettings } from "../debug/CodexSettings";
import { JsonViewer } from "../debug/JsonViewer";

export function DebugView() {
  const status = useStore((s) => s.status);

  return (
    <div className="space-y-4 max-w-6xl">
      <StopPolicy />
      <CodexSettings />
      <JsonViewer
        title="Connection diagnostics"
        data={status.connection?.diagnostics ?? { timestamp: null, items: [] }}
        testId="collapse-debug-connection"
      />
      <JsonViewer
        title="Command log"
        data={status.recent_commands ?? []}
        testId="collapse-debug-command-log"
      />
      <JsonViewer
        title="Raw status JSON"
        data={status}
        testId="collapse-debug-status-json"
      />
    </div>
  );
}
