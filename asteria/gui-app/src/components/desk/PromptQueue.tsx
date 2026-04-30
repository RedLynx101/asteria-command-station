import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { MiniCard } from "../ui/MiniCard";
import { AgentStatusBar } from "./AgentStatusBar";
import { formatTimestamp } from "../../lib/format";
import type { Prompt } from "../../lib/types";

const MODE_LABELS: Record<string, string> = {
  queue: "Queue only",
  openclaw: "OpenClaw",
  codex: "Codex",
};

function modeLabel(prompt: Prompt): string {
  return MODE_LABELS[prompt.forward_mode ?? "queue"] ?? prompt.forward_mode ?? "queue";
}

function forwardState(prompt: Prompt) {
  const mode = prompt.forward_mode ?? "queue";
  if (prompt.status === "resolved") {
    return {
      kind: "ok" as const,
      note: prompt.response
        ? `Resolved by ${prompt.resolved_label ?? "Unknown"} at ${formatTimestamp(prompt.resolved_at)}.`
        : `Resolved by ${prompt.resolved_label ?? "Unknown"}.`,
      retryId: "",
    };
  }
  if (prompt.forward_status === "sent") {
    const target = mode === "codex" ? "Codex agent" : "OpenClaw";
    return {
      kind: "success" as const,
      note: `Forwarded to ${target}${prompt.forwarded_at ? ` at ${formatTimestamp(prompt.forwarded_at)}` : ""}${prompt.bridge_session_key ? ` via ${prompt.bridge_session_key}` : ""}.`,
      retryId: "",
    };
  }
  if (prompt.forward_status === "failed") {
    return {
      kind: "warn" as const,
      note: prompt.forward_error
        ? `Forward failed: ${prompt.forward_error}`
        : "Forward failed.",
      retryId: mode === "openclaw" ? (prompt.id ?? "") : "",
    };
  }
  if (prompt.forward_status === "queued" || prompt.forward_status === "retrying") {
    const target = mode === "codex" ? "Codex" : "OpenClaw";
    return {
      kind: "pending" as const,
      note: `${prompt.forward_status === "retrying" ? "Retrying" : "Dispatching"} to ${target}...`,
      retryId: "",
    };
  }
  if (mode === "queue") {
    return {
      kind: "pending" as const,
      note: "Queued for manual pickup by any agent.",
      retryId: "",
    };
  }
  return {
    kind: "pending" as const,
    note:
      prompt.forward_error ??
      "Stored locally. Agent will only see this if the bridge is enabled.",
    retryId: "",
  };
}

export function PromptQueue() {
  const status = useStore((s) => s.status);
  const sendAction = useStore((s) => s.sendAction);

  const prompts = [...(status.prompts ?? [])].sort((a, b) => {
    const aR = a.status === "resolved" ? 1 : 0;
    const bR = b.status === "resolved" ? 1 : 0;
    if (aR !== bR) return aR - bR;
    return (b.submitted_at ?? "").localeCompare(a.submitted_at ?? "");
  });

  return (
    <Card className="w-full flex flex-col">
      <CardHeader>
        <div>
          <Eyebrow>Prompt queue</Eyebrow>
          <CardTitle>Unresolved first</CardTitle>
        </div>
        <Badge>{prompts.length} prompts</Badge>
      </CardHeader>
      <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
        {prompts.length === 0 ? (
          <MiniCard
            title="No prompts yet"
            body="Operator prompts and agent responses will appear here."
          />
        ) : (
          prompts.map((p) => {
            const fw = forwardState(p);
            const mode = p.forward_mode ?? "queue";
            const isAgentActive =
              p.status !== "resolved" &&
              (mode === "codex" || mode === "openclaw") &&
              (p.forward_status === "queued" ||
                p.forward_status === "sent" ||
                p.forward_status === "retrying");
            const agentFailed =
              p.status !== "resolved" &&
              (mode === "codex" || mode === "openclaw") &&
              p.forward_status === "failed";

            const codexJob = (status.codex_jobs ?? []).find(
              (j) => j.prompt_id === p.id,
            );
            const outputTail = codexJob?.output_tail ?? [];

            const agentSlot =
              isAgentActive ? (
                <AgentStatusBar
                  agentName={mode === "codex" ? "Codex" : "OpenClaw"}
                  promptId={p.id}
                  startedAt={p.forwarded_at ?? p.submitted_at}
                  status={
                    p.forward_status === "queued" ? "starting" : "running"
                  }
                  outputTail={outputTail}
                  onKill={
                    mode === "codex"
                      ? () =>
                          sendAction(
                            "kill_codex_job",
                            { prompt_id: p.id },
                            { leaseRequired: false },
                          )
                      : undefined
                  }
                />
              ) : agentFailed ? (
                <AgentStatusBar
                  agentName={mode === "codex" ? "Codex" : "OpenClaw"}
                  promptId={p.id}
                  status="failed"
                  error={p.forward_error}
                  outputTail={outputTail}
                />
              ) : undefined;

            return (
              <MiniCard
                key={p.id}
                title={p.status === "resolved" ? "Resolved" : "Open"}
                meta={`${modeLabel(p)} | ${p.submitted_label ?? "Unknown"} | ${formatTimestamp(p.submitted_at)} | ${p.status ?? "pending"}`}
                body={
                  p.response
                    ? `${p.text ?? ""}\n\nResponse: ${p.response}`
                    : p.text ?? ""
                }
                note={fw.note}
                kind={fw.kind}
                statusSlot={agentSlot}
                actions={
                  fw.retryId ? (
                    <Button
                      size="sm"
                      onClick={() =>
                        sendAction(
                          "retry_prompt_forward",
                          { prompt_id: fw.retryId },
                          { leaseRequired: false },
                        )
                      }
                    >
                      Retry Forward
                    </Button>
                  ) : undefined
                }
              />
            );
          })
        )}
      </div>
    </Card>
  );
}
