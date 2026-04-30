---
kind: hub
status: validated
runtime:
  - host-side
last_reviewed: 2026-04-15
---

# Stack Map

See also: [[overview/runtime-modes]], [[overview/command-surface]], [[overview/desk-prompt-bridge]], [[overview/mobile-and-handheld]], [[robot/capability-matrix]]

## Core architecture

Asteria is a host-side control stack centered on the local daemon.

```text
OpenClaw Gateway worker                 Local Codex worker
        ^                                      ^
        |  (`forward_mode=openclaw`)           |  (`forward_mode=codex`)
        |                                      |
Asteria daemon (`asteria/daemon/`)
        |
        +-- Desk prompt log + routing state
        +-- OpenClaw forward worker
        +-- Codex job runner
        +-- desktop GUI (`asteria/gui-app/`, `asteria/gui/` fallback)
        +-- mobile bridge (`asteria/mobile/`)
        |     +-- mobile session store (`artifacts/mobile-sessions/`)
        |     +-- rgb565 preview cache (`artifacts/mobile-previews/`)
        +-- FSM tooling (`asteria/tools/fsm.py`)
        +-- artifacts (`asteria/artifacts/`)
        +-- CLI (`python -m asteria.cli ...`)
        |
old-3DS handheld (`apps/asteria-ds/`)
        |
        +-- talks to `/api/mobile/*` on the same daemon
```

## Ownership boundaries

- OpenClaw is the planning/chat shell.
- The Asteria daemon is the source of truth for robot execution, safety, telemetry, control lease, and FSM lifecycle.
- The GUI is a shared human/agent surface, not a separate control backend.
- Desk prompts can stay local-only, wake OpenClaw, or spawn a local Codex worker, while prompt persistence in Asteria remains canonical.
- The mobile bridge and the 3DS client are client views over daemon state, not parallel robot runtimes.
- New clients should adapt the daemon/runtime state instead of creating parallel robot state.

## Important directories

- `asteria/daemon/`: connection logic, lease policy, action dispatch, status
- `asteria/gui-app/`: current React/Vite browser command station
- `asteria/gui/`: legacy browser command station fallback
- `asteria/mobile/`: bearer-authenticated handheld bridge mounted into the same daemon
- `apps/asteria-ds/`: old-3DS Desk/pilot client for the mobile bridge
- `asteria/tools/fsm.py`: FSM create/compile/list helpers and naming rules
- `asteria/artifacts/fsm/`: Asteria-managed FSM source and generated Python files
- `asteria/artifacts/images/`: captured robot images
- `asteria/artifacts/runs/`: compile/run artifacts
- `asteria/artifacts/mobile-sessions/`: persisted mobile chat/session artifacts
- `asteria/artifacts/mobile-previews/`: cached handheld preview files

## What the daemon currently owns

From current docs and code, `runtime.py` owns:
- robot connection state
- current runtime mode
- control lease state
- activity log and prompt log
- Desk prompt routing state and bridge status
- background Codex job tracking and timeout
- recent command log
- FSM create/compile/run flow
- latest image capture metadata
- last command result

## Design implications for the wiki

The wiki should treat the daemon-centered model as canonical. Pages should answer questions in terms of daemon behavior first, then GUI/CLI/operator views of that behavior.
