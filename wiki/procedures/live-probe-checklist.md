---
kind: procedure
status: validated
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
last_reviewed: 2026-04-15
---

# Live Probe Checklist

See also: [[overview/runtime-modes]], [[robot/safety-and-stop-semantics]], [[fsm/fsm-lifecycle]]

## Goal

Do the smallest safe sequence that tells me what Asteria can do on the live robot right now.

## Preflight

1. Read `status`.
2. Confirm target/profile is the intended one.
3. Post a short desk note for meaningful action.
4. If disconnected, connect first. Connection actions are not lease-gated.
5. Claim the lease only when you are about to send a lease-gated probe and no human holder is blocking.

## Connect and classify the runtime

1. Re-read `status`.
2. Check:
   - `connection.connected_runtime_mode`
   - `connection.supports_fsm_runtime`

Decision:
- if FSM runtime is available, continue through the full probe
- if not, stop at direct-command verification and skip live FSM steps

## Safe direct probes

1. Claim the lease if needed.
2. `capture-image`
3. `say` with short screen text
4. optionally `unload-fsm` if you need to confirm the cancel path

These are the preferred first live probes because they do not require purposeful motion.

## Safe FSM probe

If `supports_fsm_runtime == true`:
1. run `agent_smoke_test`
2. send a text event
3. send a speech event
4. decide between:
   - `stop-all --keep-fsm` if preserving the FSM is the point of the test
   - `unload-fsm` for the normal cleanup path

## Cleanup

- unload the active FSM unless there is a deliberate reason to keep it loaded
- leave a concise desk note with result and runtime mode
- record any validated quirk in the wiki
- disconnect only if the session was meant to be short-lived or isolated
