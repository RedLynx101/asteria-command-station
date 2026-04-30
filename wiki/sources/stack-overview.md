---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_file: asteria/docs/STACK_OVERVIEW.md
---

# Source Summary: Stack Overview

## Key points extracted

- The daemon is the central runtime owner.
- Desktop and mobile surfaces both route into the same daemon.
- The preferred desktop surface is now the React `gui-app`, with `gui/` retained as a fallback.
- Prompt routing now includes OpenClaw workers and local Codex workers in addition to local-only queue mode.
- New clients should adapt runtime state rather than fork control state.
- Known gaps now focus on incomplete mobile autonomous worker behavior and the remaining legacy GUI fallback.

## Wiki pages fed by this source

- [[overview/stack-map]]
- [[overview/command-surface]]
- [[open-questions]]
