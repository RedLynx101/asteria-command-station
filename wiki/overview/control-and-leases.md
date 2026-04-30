---
kind: operational
status: validated
runtime:
  - host-side
last_reviewed: 2026-04-15
---

# Control and Leases

See also: [[robot/safety-and-stop-semantics]], [[overview/command-surface]], [[procedures/recovery-playbooks]]

## Why leases exist

Lease state is how Asteria makes control ownership explicit.

The daemon tracks:
- holder id
- holder label
- holder kind (`human` or `agent`)
- priority
- expiry time

## Priority rules

Current runtime behavior:
- human holders outrank agents
- an agent should not preempt a human holder
- if a human holds the lease, wait and report
- reusing your own active lease is allowed

This matches the operating guidance in workspace memory and Asteria docs.

## What requires a lease

From `runtime.py` dispatch behavior:

### No lease required
- `status`
- `connect`
- `disconnect`
- `reconnect`
- `create_fsm`
- `compile_fsm`
- desk/prompt actions
- connection configuration/diagnostics

### Lease required
- `run_fsm`
- `unload_fsm`
- `send_text`
- `send_speech`
- `stop_all`
- `capture_image`
- `move`
- `sideways`
- `turn`
- `drive_at`
- `turn_at`
- `say`
- `kick`

## Shared desk rule

Meaningful planning and execution updates should be visible in the Desk activity feed. The desk is for coordination, not telemetry spam.

## Agent rule of thumb

- host-side file preparation can happen without a lease
- any live robot-affecting action should assume lease discipline
- `connect` / `disconnect` are not lease-gated in code, but they still change shared robot availability and should be coordinated like live operations
- if the human is `local-gui` or otherwise active, do not force preemption
