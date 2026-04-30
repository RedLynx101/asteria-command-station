---
kind: operational
status: mixed
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
  - host-side
last_reviewed: 2026-04-15
---

# Command Surface

See also: [[robot/capability-matrix]], [[fsm/fsm-lifecycle]], [[overview/desk-prompt-bridge]], [[overview/mobile-and-handheld]], [[sources/cli-surface]], [[sources/gui-app-surface]]

## Main surfaces

### GUI
Tabs documented in current Asteria docs:
- Operations
- Desk
- FSM
- Vision
- Debug

The daemon serves the React GUI build from `asteria/gui-app/dist` when present and falls back to the legacy `asteria/gui/` surface otherwise.

The GUI uses daemon endpoints rather than owning separate robot state.

Operationally important current GUI facts:
- Operations supports both discrete step commands (`move`, `sideways`, `turn`) and an optional continuous hold mode that maps forward/back/strafe/turn into `drive_at` / `turn_at`.
- Desk prompts can now be routed as `queue`, `openclaw`, or `codex`.
- Debug includes Codex timeout and kill controls in addition to diagnostics.

### Mobile / handheld
The same daemon also exposes a mobile surface under `/api/mobile/*`.

Operationally important pieces:
- status/bootstrap
- Desk prompt submission
- teleop claim/release
- teleop command/vector routes
- latest image access plus cached preview generation

The current 3DS app uses that mobile surface as a Desk-and-pilot client, not as a true autonomous mobile chat worker.

### CLI
Primary local interface:
- `python -m asteria.cli status`
- `python -m asteria.cli connect`
- `python -m asteria.cli list-prompts --pending-only --limit 10`
- `python -m asteria.cli stop-all`
- `python -m asteria.cli unload-fsm`
- `python -m asteria.cli run-fsm --module <name>`
- `python -m asteria.cli send-text --message <text>`
- `python -m asteria.cli send-speech --message <text>`

Important CLI nuance:
- `submit-prompt` currently exposes only `--text`, so plain CLI prompt submission defaults to `forward_mode=queue`.
- The extra Desk routing modes are currently exposed through the daemon API and the React GUI, not through a dedicated CLI flag.

### Repo-local helper wrappers
Preferred agent path:
- `python asteria/openclaw/skills/asteria-command-station/helpers/asteriactl.py ...`
- `python asteria/openclaw/skills/asteria-command-station/helpers/asteria_cycle.py ...`

These wrappers align with Asteria's expected operator surface and auto-claim when safe.

## Command classes

### Host-side prep
- create FSM source
- compile FSM source
- list FSM files
- inspect status
- configure connection target
- connect / disconnect / reconnect
- list desk prompts / retry prompt forward

### Desk / coordination
- submit prompt
- list prompts
- resolve prompt
- retry prompt forward
- log note

### Live direct robot actions
- capture image
- display text (`say`)
- kick
- move / turn / sideways (discrete)
- drive_at / turn_at (continuous)
- stop

### Live FSM actions
- run a compiled module
- send text event
- send speech event
- unload active FSM

## Important parameter notes

Current CLI surface uses:
- `run-fsm --module`, not `--name`
- `send-text --message`, not `--text`
- `send-speech --message`, not `--text`
- `stop-all --keep-fsm` to halt motion while preserving the loaded FSM

## Desk prompt routing

The Desk now has three routing modes:
- `queue`: store locally and leave the prompt for manual pickup; this shows up as `forward_status=not_sent`
- `openclaw`: store locally, then queue background forwarding to Gateway `POST /v1/responses`
- `codex`: store locally, then spawn a background local Codex worker tracked through `status.codex_jobs`

Important current state semantics:
- `prompt.status=resolved` means the task was closed out back in Asteria
- `prompt.forward_status=sent` means the downstream worker accepted or started the run
- for `openclaw`, `sent` means OpenClaw accepted the turn
- for `codex`, `sent` means the local Codex job was started
- neither meaning implies the prompt is already resolved

OpenClaw-specific routing details:
- session routing uses the `X-OpenClaw-Session-Key` header, not a JSON `session_key` field
- prompts default to prompt-specific session keys derived from `session:asteria-desk`
- if forwarding fails, the prompt still remains visible through `list-prompts` for manual recovery

Codex-specific routing details:
- the daemon tracks live workers in `status.codex_jobs`
- the server-side timeout is exposed as `status.codex_timeout_minutes`
- the Debug tab can change the timeout and kill active Codex jobs

## Recommendation

For agent work, think in this order:
1. status
2. check unresolved desk prompts
3. connection/runtime check
4. lease/desk discipline
5. direct command vs continuous hold teleop vs FSM decision
6. run bounded action
7. stop/unload intentionally
