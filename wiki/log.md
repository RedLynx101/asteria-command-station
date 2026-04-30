---
kind: notes
status: active
last_reviewed: 2026-04-15
---

# Wiki Log

## [2026-04-14] bootstrap | initial Asteria wiki build
- Created the first agent-oriented wiki scaffold under `asteria/asteria_wiki/`.
- Added hub pages for stack overview, runtime modes, control ownership, command surface, safety, and FSM workflow.
- Added a capability matrix focused on direct commands versus live FSM behavior.
- Ingested the user-shared `llm-wiki.md` note as an immutable raw source copy plus a source summary.
- Added source summaries for the current Asteria docs, CLI surface, FSM tooling, and validated live notes.
- Mined the repo FSM corpus into [[fsm/example-fsms]] and [[fsm/fsm-authoring-patterns]].
- Recorded open gaps and follow-up questions in [[open-questions]].

## [2026-04-14] bridge | direct Desk -> OpenClaw bridge validated
- Updated the wiki to reflect the working Desk prompt bridge through OpenClaw Gateway `POST /v1/responses`.
- Added the bridge path to [[overview/stack-map]] and the operational forwarding notes to [[overview/command-surface]].
- Synced the source layer to include [[sources/openclaw-direct-bridge]].
- Corrected stale path references that still pointed at `asteria/wiki/` instead of `asteria/asteria_wiki/`.

## [2026-04-14] gaps | Desk/mobile/3DS coverage expanded
- Added dedicated operational pages for [[overview/desk-prompt-bridge]] and [[overview/mobile-and-handheld]].
- Expanded recovery notes for prompt-forward failures, stale `sent` prompts, handheld preview issues, and daemon-up/robot-down cases.
- Refreshed [[overview/stack-map]], [[overview/command-surface]], and [[robot/capability-matrix]] to cover prompt queueing, prompt-specific bridge sessions, mobile teleop, and cached handheld previews.
- Added code-derived source summaries for the current prompt runtime and mobile/handheld surface.
- Recorded current documentation mismatches in [[open-questions]] instead of leaving them implicit.

## [2026-04-15] audit | repo-grounded wiki refresh
- Re-audited the wiki against current repo code instead of older notes, with `runtime.py`, `server.py`, `gui-app`, `mobile/runtime_adapter.py`, and the repo docs used as the main ground truth.
- Updated the wiki to describe the current three-mode Desk routing model: `queue`, `openclaw`, and `codex`.
- Corrected control-surface docs so direct motion distinguishes discrete `move` / `sideways` / `turn` from continuous `drive_at` / `turn_at`.
- Corrected lease docs so `connect` / `disconnect` / `reconnect` are no longer described as lease-gated.
- Added [[sources/gui-app-surface]] so the React desktop GUI now has a direct source-summary layer in the wiki.
- Refreshed repo-facing source summaries after updating the underlying `README.md`, `STACK_OVERVIEW.md`, and `OPERATOR_RUNBOOK.md`.
