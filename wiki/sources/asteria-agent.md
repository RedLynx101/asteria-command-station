---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_file: asteria/ASTERIA_AGENT.md
---

# Source Summary: Asteria Agent Instructions

## Key points extracted

- The daemon is the source of truth for robot status and execution.
- Use direct commands for bounded one-step actions.
- Use FSMs for multi-step, looping, or event-driven behavior.
- Stop policy must be explicit: `stop-all`, `stop-all --keep-fsm`, `unload-fsm` each mean different things.
- Reporting and desk narration are part of normal operation.
- The wiki should only record validated behavior and should mark uncertainty clearly.

## Wiki pages fed by this source

- [[overview/control-and-leases]]
- [[robot/safety-and-stop-semantics]]
- [[fsm/fsm-lifecycle]]
