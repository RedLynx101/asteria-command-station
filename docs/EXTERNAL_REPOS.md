# External Repositories And Runtime Dependencies

Asteria is intentionally public and compact. It references several local systems without vendoring them.

## Sibling Repo

- [RedLynx101/asteria-ds](https://github.com/RedLynx101/asteria-ds)
  Old-3DS homebrew client that talks to Asteria's authenticated mobile bridge.

## Live Robot Dependencies

For disconnected GUI, CLI, wiki, and FSM review, no robot dependency repo is required.

For live VEX AIM control, clone these into the `asteria-command-station/` repo root:

```text
asteria-command-station/
  asteria/
  vex-aim-tools/
  AIM_Websocket_Library/
```

The daemon adds those folders to `sys.path` if present. If they are missing, Asteria still starts, but live connection and runtime-backed FSM execution will not work.

## Dependency Roles

- [`touretzkyds/vex-aim-tools`](https://github.com/touretzkyds/vex-aim-tools)
  Provides `aim_fsm`, `aim_fsm.program`, `aim_fsm.events`, and `genfsm`. Asteria uses these for live FSM loading, event injection, and `.fsm` to Python compilation.
- [`touretzkyds/AIM_Websocket_Library`](https://github.com/touretzkyds/AIM_Websocket_Library)
  Provides the `vex` Python package used by the VEX AIM WebSocket robot transport. Asteria's live runtime imports it when connecting to hardware.

Suggested setup:

```powershell
cd asteria-command-station
git clone https://github.com/touretzkyds/vex-aim-tools.git
git clone https://github.com/touretzkyds/AIM_Websocket_Library.git
```

Both folders are ignored by this repo's `.gitignore`; they remain separate upstream projects.

## Optional OpenClaw Gateway

OpenClaw is an external planning/chat shell. Asteria keeps the robot runtime local and can forward Desk prompts through an OpenClaw-compatible gateway when configured.

Relevant environment variables:

```text
ASTERIA_OPENCLAW_BRIDGE_ENABLED
ASTERIA_OPENCLAW_GATEWAY_URL
ASTERIA_OPENCLAW_GATEWAY_PATH
ASTERIA_OPENCLAW_GATEWAY_TOKEN
ASTERIA_OPENCLAW_SESSION_KEY
ASTERIA_OPENCLAW_SESSION_KEY_TEMPLATE
ASTERIA_OPENCLAW_BRIDGE_TIMEOUT_MS
ASTERIA_OPENCLAW_BRIDGE_MODEL
ASTERIA_OPENCLAW_BRIDGE_USER
ASTERIA_OPENCLAW_AUTO_START
```

The public repo keeps `asteria/openclaw_bridge.py` because it is Asteria-side integration code. It does not include the OpenClaw repo or vendored OpenClaw skills.
