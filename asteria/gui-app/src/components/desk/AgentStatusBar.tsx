import { useEffect, useState } from "react";
import { Loader2, Bot, Zap, X, ChevronDown, ChevronUp, Terminal } from "lucide-react";

interface AgentStatusBarProps {
  agentName: string;
  promptId: string;
  startedAt?: string;
  status: "starting" | "running" | "failed";
  error?: string;
  outputTail?: string[];
  onKill?: () => void;
}

function elapsed(since?: string): string {
  if (!since) return "";
  const ms = Date.now() - new Date(since).getTime();
  if (Number.isNaN(ms) || ms < 0) return "";
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return `${mins}m ${rem}s`;
}

export function AgentStatusBar({
  agentName,
  startedAt,
  status,
  error,
  outputTail,
  onKill,
}: AgentStatusBarProps) {
  const [, tick] = useState(0);
  const [outputOpen, setOutputOpen] = useState(false);

  useEffect(() => {
    if (status === "failed") return;
    const id = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [status]);

  const lines = outputTail ?? [];
  const hasOutput = lines.length > 0;

  if (status === "failed") {
    return (
      <div className="rounded-lg bg-danger-soft border border-danger/20 overflow-hidden">
        <div className="flex items-center gap-2.5 px-3 py-2">
          <Zap size={14} className="text-danger shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold text-danger">
              {agentName} failed
            </div>
            {error && (
              <div className="text-[11px] text-danger/70 mt-0.5 line-clamp-2">
                {error}
              </div>
            )}
          </div>
          {hasOutput && (
            <button
              onClick={() => setOutputOpen(!outputOpen)}
              className="flex items-center gap-1 text-[10px] text-danger/60 hover:text-danger transition-colors cursor-pointer shrink-0"
            >
              <Terminal size={11} />
              {outputOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
          )}
        </div>
        {outputOpen && hasOutput && (
          <div className="border-t border-danger/10 px-3 py-2 max-h-[160px] overflow-y-auto">
            <pre className="text-[10px] font-mono text-danger/70 leading-relaxed whitespace-pre-wrap break-words">
              {lines.slice(-20).join("\n")}
            </pre>
          </div>
        )}
      </div>
    );
  }

  const isStarting = status === "starting";
  const time = elapsed(startedAt);

  return (
    <div className="relative overflow-hidden rounded-lg border border-accent/25">
      <div className="absolute inset-0 bg-accent-soft" />
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/10 to-transparent animate-[shimmer_2s_infinite]" />

      <div className="relative">
        <div className="flex items-center gap-2.5 px-3 py-2">
          <div className="relative flex items-center justify-center w-6 h-6 shrink-0">
            <Loader2 size={18} className="text-accent animate-spin" />
            <Bot size={10} className="absolute text-accent" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-accent">
                {isStarting ? `Starting ${agentName}...` : `${agentName} working`}
              </span>
              {time && (
                <span className="text-[10px] text-accent/60 font-mono tabular-nums">
                  {time}
                </span>
              )}
            </div>
            <div className="text-[10px] text-secondary mt-0.5">
              {isStarting
                ? "Initializing agent session"
                : "Agent is autonomously processing this prompt"}
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {hasOutput && (
              <button
                onClick={() => setOutputOpen(!outputOpen)}
                className="flex items-center gap-1 h-6 px-1.5 text-[10px] text-accent/60 hover:text-accent bg-accent/5 hover:bg-accent/10 border border-accent/15 rounded transition-colors cursor-pointer"
                title="Toggle output"
              >
                <Terminal size={11} />
                {outputOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              </button>
            )}
            {onKill && (
              <button
                onClick={onKill}
                className="flex items-center justify-center h-6 w-6 text-danger/60 hover:text-danger hover:bg-danger-soft rounded transition-colors cursor-pointer"
                title="Kill agent"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
          </span>
        </div>

        {outputOpen && hasOutput && (
          <div className="border-t border-accent/15 px-3 py-2 max-h-[160px] overflow-y-auto bg-bg-inset/50">
            <pre className="text-[10px] font-mono text-secondary leading-relaxed whitespace-pre-wrap break-words">
              {lines.slice(-20).join("\n")}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
