---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_file: asteria/docs/OPENCLAW_SETUP.md
---

# Source Summary: OpenClaw Setup

## Key points extracted

- OpenClaw should not talk to the robot runtime directly.
- The repo-local Asteria command-station skill is the intended agent surface.
- The helper wrappers are preferred over ad hoc raw commands.
- The full-first runtime policy and the meaning of `connected_runtime_mode` / `supports_fsm_runtime` are explicitly documented.

## Wiki pages fed by this source

- [[overview/stack-map]]
- [[overview/runtime-modes]]
- [[overview/command-surface]]
