# OpenClaw Setup For Asteria

This document describes the Asteria-facing layer that OpenClaw should use.

## Principle

OpenClaw should not talk to the robot runtime directly.

Use this stack:

1. OpenClaw for planning, chat, and tool invocation
2. Asteria daemon for robot execution, safety, FSM lifecycle, telemetry, and the shared desk
3. The Asteria GUI as the human/agent command surface

## Repo-local skill bundle

Use the repo-local skill bundle at:

`asteria/openclaw/skills/asteria-command-station`

Key files:

- `asteria/openclaw/skills/asteria-command-station/SKILL.md`
- `asteria/openclaw/skills/asteria-command-station/helpers/asteriactl.py`
- `asteria/openclaw/skills/asteria-command-station/helpers/asteria_cycle.py`

## Recommended usage model

If your OpenClaw session already has access to this repo, the simplest approach is:

- tell OpenClaw where this repo lives
- tell it to use the skill at `asteria/openclaw/skills/asteria-command-station/SKILL.md`

That avoids a second install/copy step.

If later you want persistent skill discovery outside this repo, copy the skill folder into your OpenClaw skills area.

## Standard commands

Start Asteria:

```powershell
python asteria/openclaw/skills/asteria-command-station/helpers/asteriactl.py start-daemon --profile home
```

Check status:

```powershell
python asteria/openclaw/skills/asteria-command-station/helpers/asteriactl.py status
```

Lease-gated helper commands auto-claim the agent lease before execution. If a human holder currently owns the lease, the helper will stop instead of preempting that human.

## Live runtime note

The daemon now connects with an automatic runtime policy:

- first try `aim_fsm_headless`
- if that fails, fall back to `aim_raw_minimal`

That means:

- `aim_fsm_headless`: direct commands, telemetry, image capture, live FSM execution, and FSM event injection
- `aim_raw_minimal`: direct commands, telemetry, screen text, and image capture, but no live FSM execution or FSM event injection

Always check `status.connection.connected_runtime_mode` and `status.connection.supports_fsm_runtime` before assuming FSM features are available on live hardware.

Post a note into the shared desk:

```powershell
python asteria/openclaw/skills/asteria-command-station/helpers/asteriactl.py log-note --title "Planning" --message "Asteria is preparing the next action."
```

Run deterministic FSM flow:

```powershell
python asteria/openclaw/skills/asteria-command-station/helpers/asteria_cycle.py ensure-run --name openclaw_probe
```

## Shared-desk expectation

OpenClaw should use the shared desk intentionally:

- post planning notes
- acknowledge or resolve operator prompts
- avoid silent high-impact actions
- rely on the direct Desk -> OpenClaw bridge as the fast path, but still use `list-prompts` as the fallback audit loop when forwarding fails

## Asteria wiki expectation

The Asteria agent should maintain a living wiki over time under:

`asteria/asteria_wiki/`

That is not the current build task, but it is part of the long-term operating model for validated robot knowledge.
