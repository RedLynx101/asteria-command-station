---
kind: source-summary
status: mixed
last_reviewed: 2026-04-15
source_files:
  - asteria/mobile/bridge.py
  - asteria/mobile/runtime_adapter.py
  - ../asteria-ds/README.md
  - ../asteria-ds/source/main.cpp
  - ../asteria-ds/source/ui.cpp
---

# Source Summary: Mobile Runtime Surface

## Key points extracted

- The mobile bridge is mounted into the daemon and handles auth, status projection, teleop state, prompt submission, preview generation, and legacy session storage.
- The runtime adapter now maps vector teleop into `drive_at` / `turn_at`, not just discrete step commands.
- `grab_assist` from the mobile surface currently falls back to a soft kick, while `place` remains unsupported.
- The 3DS client's Chat tab is now a Desk prompt surface aimed at `/api/mobile/prompt`, not a live autonomous mobile chat worker.
- The handheld preview path uses cached `rgb565` preview generation and serves `/api/mobile/images/preview` for direct 3DS consumption.
- The mobile stop path intentionally keeps `stop_fsm=false`, so letting go of handheld teleop does not unload an active FSM.

## Wiki pages fed by this source

- [[overview/mobile-and-handheld]]
- [[overview/command-surface]]
- [[robot/capability-matrix]]
- [[open-questions]]
