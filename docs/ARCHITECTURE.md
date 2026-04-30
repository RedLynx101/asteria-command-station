# Architecture

Asteria is a local-first robotics control stack.

## Runtime Boundary

The daemon owns:

- robot connection state
- control leases
- bounded direct commands
- FSM creation, compilation, and execution requests
- Desk prompts and activity notes
- image capture summaries
- mobile bridge sessions
- stop and unload semantics

The desktop GUI, mobile clients, and agents all talk to the daemon instead of each owning robot state.

## Surfaces

- Desktop GUI: operator-oriented command station served by the daemon.
- CLI: scriptable agent and operator control surface.
- Mobile bridge: authenticated API for lightweight handheld clients.
- Wiki: durable knowledge base for validated behavior and recovery procedures.
- FSM examples: reusable behavior programs and diagrams under `asteria/artifacts/fsm/`.

## Agent Flow

1. Read status.
2. Check the current lease and active FSM.
3. Claim control only when needed.
4. Use direct commands for bounded probes.
5. Write or edit an FSM for multi-step behavior.
6. Log notes and resolve Desk prompts so the human operator can audit what happened.
7. Stop or unload intentionally before handing back control.

## Why This Matters

The same system can be used as:

- a pair-programming repo for FSM and UI work
- an autonomous agent runtime with explicit safety boundaries
- a teaching artifact for command dispatch, leases, finite state machines, and human-agent collaboration
