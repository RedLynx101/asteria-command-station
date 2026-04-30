# Roadmap

Asteria is already usable as a disconnected command station, FSM workspace, mobile bridge, and agent coordination surface. The next useful work should keep the public repo compact and runnable.

## Near Term

- Add focused tests for daemon dispatch, lease behavior, mobile auth, and FSM helper functions.
- Keep improving the Desk prompt workflow so human and agent actions remain auditable.
- Add small tutorial FSMs that teach state transitions, events, and stop handling.
- Keep the wiki synced with validated behavior rather than speculative notes.

## Live Runtime

- Keep the daemon disconnected-friendly.
- Treat `vex-aim-tools/` and `AIM_Websocket_Library/` as external live-robot dependencies.
- Make connection errors clear when those external folders are missing.
- Preserve explicit stop and unload semantics for both humans and agents.

## Handheld Pair

- Keep the mobile bridge stable for Asteria DS.
- Maintain `scripts/asteria_mobile_setup.py` as the config handoff path.
- Document bridge changes in both this repo and the sibling `asteria-ds` repo.
