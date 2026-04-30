# External Repositories And Runtime Dependencies

Asteria is intentionally public and compact. It references several local systems without vendoring them.

## Sibling Repo

- `../asteria-ds`
  Old-3DS homebrew client that talks to Asteria's authenticated mobile bridge.

## Live Robot Dependencies

For disconnected GUI, CLI, wiki, and FSM review, no robot dependency repo is required.

For live VEX AIM control, place these beside the repo root when available:

```text
asteria-command-station/
vex-aim-tools/
AIM_Websocket_Library/
```

The daemon adds those folders to `sys.path` if present. If they are missing, Asteria still starts, but live connection and runtime-backed FSM execution will not work.

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
