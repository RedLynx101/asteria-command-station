---
kind: operational
status: validated
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
last_reviewed: 2026-04-15
---

# Runtime Modes

See also: [[robot/capability-matrix]], [[fsm/fsm-lifecycle]], [[procedures/recovery-playbooks]]

## The two live modes

Asteria tries to connect in this order:
1. `aim_fsm_headless`
2. `aim_raw_minimal`

This full-first policy is documented in the current Asteria docs and reflected in `runtime.py`.

## `aim_fsm_headless`

Use this when live FSM execution matters.

### What it supports
- direct commands
- image capture
- live FSM execution
- FSM event injection (`send-text`, `send-speech`)
- headless full AIM runtime without the normal viewer windows

### Current validated live facts
- confirmed live on 2026-04-14
- `supports_fsm_runtime: true`
- safe non-motion probes succeeded
- `agent_smoke_test` ran live and accepted both text and speech events

## `aim_raw_minimal`

Compatibility fallback when full AIM cannot connect cleanly.

### What it supports
- direct commands
- telemetry
- screen text
- image capture

### What it does not support
- live FSM execution
- FSM event injection

If `supports_fsm_runtime: false`, treat all run/message-FSM actions as unavailable on live hardware.

## How to inspect the mode

Check the status fields:
- `connection.connected_runtime_mode`
- `connection.supports_fsm_runtime`

These are the fastest truth checks before deciding between a direct command and an FSM workflow.

## Practical rule

- If the task is multi-step or event-driven and `supports_fsm_runtime` is true, prefer an FSM.
- If the daemon fell back to minimal mode, use direct commands and host-side FSM prep only.
