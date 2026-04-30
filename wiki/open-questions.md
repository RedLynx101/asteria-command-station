---
kind: open-questions
status: active
last_reviewed: 2026-04-16
---

# Open Questions

## Validation gaps

- `kick` exists in the daemon and CLI surface, but it was not revalidated in this wiki pass.
- direct motion commands exist and are safety-bounded, but they were intentionally not re-tested here.
- the mobile bridge now has validated 3DS-facing Desk/pilot paths, but the older `/api/mobile/chat/sessions` surface still lacks a validated autonomous worker behind it.
- the updated split `soccer_tag0_shot` helper now uses AI-vision-assisted `AprilTag-0` search/aim logic, but that revised helper still needs a fresh live validation pass after the latest code change.
- a live retest showed `PickUp(BALL_SPEC)` can remain active even with the soccer ball visibly pressed against the lower foreground, so the exact completion conditions of the stock pickup node remain an unresolved runtime question.

## Compatibility questions

- Which lab FSMs can run in the current headless Asteria environment without viewer or environment-specific breakage?
- Which perception-heavy examples depend on extra local assets or model weights that are not yet tracked in a clean source summary?
- Which world-map/navigation examples are realistic templates for current live hardware versus course-only exercises?
- Should the legacy mobile session/chat endpoints remain exposed if the primary handheld path is now Desk prompts plus teleop?

## Workflow questions

- Should the wiki eventually add per-FSM pages for the highest-value examples instead of one shared pattern library page?
- Should a machine-generated inventory page be maintained automatically from the FSM corpus?
- Should Dataview or local markdown search be added later once the wiki grows beyond simple index navigation?
