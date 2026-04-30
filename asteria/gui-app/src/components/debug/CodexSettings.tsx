import { useState } from "react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Button } from "../ui/Button";

export function CodexSettings() {
  const status = useStore((s) => s.status);
  const sendAction = useStore((s) => s.sendAction);
  const currentTimeout = status.codex_timeout_minutes ?? 20;
  const currentModel = status.codex_model ?? "gpt-5.4-mini";
  const [minutes, setMinutes] = useState(String(currentTimeout));
  const activeJobs = (status.codex_jobs ?? []).filter((j) => j.alive);

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Codex agent</Eyebrow>
          <CardTitle>Agent settings</CardTitle>
        </div>
      </CardHeader>
      <div className="space-y-3">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-[11px] font-medium text-secondary mb-1">
              Timeout (minutes, 1-60)
            </label>
            <input
              type="number"
              min={1}
              max={60}
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              className="w-full h-8 px-2.5 text-sm bg-surface-raised border border-border rounded-lg text-primary outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <Button
            size="sm"
            onClick={() =>
              sendAction(
                "set_codex_timeout",
                { minutes: parseInt(minutes, 10) },
                { leaseRequired: false },
              )
            }
          >
            Apply
          </Button>
        </div>
        <p className="text-[11px] text-tertiary">
          Model: <strong>{currentModel}</strong>.{" "}
          Current server timeout: <strong>{currentTimeout} min</strong>.
          Active Codex jobs: <strong>{activeJobs.length}</strong>.
        </p>
        {activeJobs.length > 0 && (
          <div className="space-y-1.5">
            {activeJobs.map((job) => (
              <div
                key={job.pid}
                className="flex items-center justify-between gap-2 px-3 py-2 bg-surface-raised border border-border rounded-lg text-xs"
              >
                <div className="min-w-0">
                  <span className="text-primary font-medium">
                    {job.prompt_id}
                  </span>
                  <span className="text-tertiary ml-2">PID {job.pid}</span>
                  {job.model && (
                    <span className="text-tertiary ml-2">{job.model}</span>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="danger-ghost"
                  onClick={() =>
                    sendAction(
                      "kill_codex_job",
                      { prompt_id: job.prompt_id },
                      { leaseRequired: false },
                    )
                  }
                >
                  Kill
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
