---
kind: source-summary
status: mixed
last_reviewed: 2026-04-15
source_file: asteria/cli.py
---

# Source Summary: CLI Surface

## Key points extracted

- The CLI exposes status, lease, connection, direct commands, desk actions, FSM lifecycle actions, and event injection.
- Connection tooling includes `set-connection`, `save-profile-target`, `diagnose-connection`, `connect`, `disconnect`, and `reconnect`.
- The CLI's direct motion surface is still discrete (`move`, `sideways`, `turn`); continuous `drive_at` / `turn_at` live in the GUI/mobile surfaces instead.
- Important parameter names are part of the current truth surface, especially:
  - `run-fsm --module`
  - `send-text --message`
  - `send-speech --message`
  - `stop-all --keep-fsm`
- `list-prompts --pending-only --limit <n>` is the main queue inspection path.
- `submit-prompt` currently accepts only `--text`, so CLI prompt submission defaults to `forward_mode=queue`.
- `say` means display text on the robot screen, not speech synthesis.

## Wiki pages fed by this source

- [[overview/command-surface]]
- [[robot/capability-matrix]]
- [[fsm/fsm-lifecycle]]
