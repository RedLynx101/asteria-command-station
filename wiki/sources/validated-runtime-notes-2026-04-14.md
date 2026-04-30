---
kind: source-summary
status: validated
last_reviewed: 2026-04-14
source_files:
  - original-workspace/MEMORY.md
  - original-workspace/memory/2026-04-14.md
---

# Source Summary: Validated Runtime Notes (2026-04-14)

## Key points extracted

- The live stack successfully connected in `aim_fsm_headless` on the `home` profile.
- `supports_fsm_runtime` was true in the validated live pass.
- Safe non-motion probes succeeded: image capture, screen text, unload.
- `agent_smoke_test` ran live and accepted both text and speech events.
- `stop-all --keep-fsm` preserved the active FSM, and `unload-fsm` then cleared it.
- These notes are the strongest current live evidence for the wikiâ€™s operational pages.

## Wiki pages fed by this source

- [[overview/runtime-modes]]
- [[robot/capability-matrix]]
- [[robot/safety-and-stop-semantics]]
- [[fsm/fsm-lifecycle]]
