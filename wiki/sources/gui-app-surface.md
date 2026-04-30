---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_files:
  - asteria/gui-app/src/components/views/OperationsView.tsx
  - asteria/gui-app/src/components/operations/TeleopController.tsx
  - asteria/gui-app/src/components/desk/PromptComposer.tsx
  - asteria/gui-app/src/components/desk/PromptQueue.tsx
  - asteria/gui-app/src/components/debug/CodexSettings.tsx
  - asteria/gui-app/src/lib/store.ts
  - asteria/daemon/server.py
---

# Source Summary: GUI App Surface

## Key points extracted

- The daemon prefers the React GUI build from `gui-app/dist` and falls back to legacy `gui/` only when needed.
- The main desktop views are still `Operations`, `Desk`, `FSM`, `Vision`, and `Debug`.
- Operations now supports both discrete step commands and an optional continuous hold mode that maps into `drive_at` / `turn_at`.
- The GUI does not auto-claim or auto-renew leases unless the local GUI session explicitly claimed control first.
- Desk prompt submission now exposes three forward modes: `queue`, `openclaw`, and `codex`.
- Prompt cards render mode-aware status, including OpenClaw forward state and live Codex job output.
- Debug exposes server-side Codex timeout changes and active-job kill controls.

## Wiki pages fed by this source

- [[overview/command-surface]]
- [[overview/stack-map]]
- [[overview/desk-prompt-bridge]]
- [[robot/capability-matrix]]
