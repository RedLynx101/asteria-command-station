---
kind: operational
status: validated
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
last_reviewed: 2026-04-15
---

# Safety and Stop Semantics

See also: [[overview/control-and-leases]], [[robot/capability-matrix]], [[procedures/live-probe-checklist]]

## Default safety posture

Treat `unload-fsm` as the normal cancellation path when the live FSM itself is the thing being stopped.

Use `stop-all --keep-fsm` only when preserving the loaded FSM is intentional.

## Current stop options

### `stop-all`
Immediate motion halt. Current default behavior also unloads the active FSM.

### `stop-all --keep-fsm`
Immediate motion halt, but leaves the active FSM loaded.

This is less safe because the FSM may still react to later events.

### `unload-fsm`
Stops the running FSM and clears it from the runtime.

## Validated behavior

Live validation on 2026-04-14 confirmed:
- `stop-all --keep-fsm` halted motion while leaving the FSM loaded
- the loaded FSM still accepted a later text event
- `unload-fsm` then cleared the active FSM successfully

That means preserving an FSM is real behavior, not just a UI toggle.

## Practical policy

- If uncertainty is high, unload.
- If you are done inspecting or messaging an FSM, unload.
- If a human is collaborating and wants to inspect state without rerunning the program, `--keep-fsm` is the special-case tool.
- Do not treat `--keep-fsm` as the default stop path.

## Additional safety notes

- The daemon now issues direct move/turn non-blocking so stop can preempt instead of waiting behind a movement call.
- A safe first live probe should still be non-motion, usually `capture-image`.
- Human lease ownership always wins over agent convenience.
