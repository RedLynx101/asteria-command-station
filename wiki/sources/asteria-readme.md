---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_file: asteria/README.md
---

# Source Summary: Asteria README

## Key points extracted

- Asteria is the host-side control stack for this repo.
- The current stack combines daemon, GUI, mobile bridge, and shared tooling.
- The README now distinguishes the primary React GUI (`gui-app/dist`) from the legacy `gui/` fallback.
- The GUI tab model and main daemon endpoints are documented here.
- Desk routing is now described as `queue`, `openclaw`, or `codex`, not just as a single OpenClaw bridge.
- The runtime connects full-first: `aim_fsm_headless` before `aim_raw_minimal`.
- The mobile bridge is mounted into the same daemon, not a separate server.

## Wiki pages fed by this source

- [[overview/stack-map]]
- [[overview/runtime-modes]]
- [[overview/command-surface]]
