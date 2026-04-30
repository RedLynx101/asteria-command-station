# Asteria Operator Runbook

## Start

```powershell
powershell -ExecutionPolicy Bypass -File .\asteria\use_asteria_env.ps1 -Profile home -Show
powershell -ExecutionPolicy Bypass -File .\asteria\start_asteria.ps1
```

The Asteria start flow prefers the repo-local `env-win` Python when it exists.

Open:

```text
http://127.0.0.1:8766/
```

## Stop

```powershell
powershell -ExecutionPolicy Bypass -File .\asteria\stop_asteria.ps1
```

## Quick CLI Checks

```powershell
python -m asteria.cli status
python -m asteria.cli --holder-id openclaw --holder-label OpenClaw --holder-kind agent claim-lease --force
python -m asteria.cli --holder-id openclaw create-fsm --name openclaw_probe
python -m asteria.cli --holder-id openclaw compile-fsm --name openclaw_probe
python -m asteria.cli --holder-id openclaw --holder-label OpenClaw --holder-kind agent list-prompts --pending-only --limit 10
python -m asteria.cli --holder-id openclaw --holder-label OpenClaw --holder-kind agent log-note --title "Planning" --message "Asteria is online"
python -m asteria.cli --holder-id openclaw --holder-label OpenClaw --holder-kind agent submit-prompt --text "Inspect the active FSM"
```

## GUI Orientation

- Use the `Operations` tab for:
  - connection targeting
  - direct motion/kick/capture actions
  - optional continuous hold teleop through `drive_at` / `turn_at`
  - latest result feedback and quick telemetry
- Use the `Desk` tab to:
  - submit operator prompts for Asteria/OpenClaw
  - choose whether a prompt stays local (`queue`), goes to OpenClaw, or spawns a Codex worker
  - log notes into the shared activity feed
  - watch prompt resolution and recent agent actions
- Use the `FSM` tab for file editing, compile/run, and event injection.
- Use the `Vision` tab for the large image viewer and recent command log.
- Use the `Debug` tab for diagnostics, raw JSON, and Codex timeout / kill controls.

## Current Caveats

- Safe live robot probes and selected FSM flows have been validated, but not every motionful workflow has been re-tested recently.
- `connect` / `disconnect` are not lease-gated in code, but any live actuation, image capture, or FSM run still requires normal lease discipline.
- Desk prompts now depend on their selected forward mode (`queue`, `openclaw`, or `codex`), so inspect prompt state instead of assuming every Desk prompt goes to OpenClaw.
