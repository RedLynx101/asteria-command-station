---
kind: procedure
status: mixed
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
  - host-side
last_reviewed: 2026-04-15
---

# Recovery Playbooks

See also: [[overview/control-and-leases]], [[overview/runtime-modes]], [[overview/desk-prompt-bridge]], [[overview/mobile-and-handheld]], [[open-questions]]

## Lease blocked by human holder

Symptoms:
- status shows a human holder such as `local-gui`
- lease claim is refused

Response:
- do not force preemption
- post/resolve via the Desk if coordination is needed
- wait and report

## Connected, but `supports_fsm_runtime: false`

Meaning:
- the daemon fell back to `aim_raw_minimal`
- direct commands and image capture still work
- live FSM run/event injection do not

Response:
- switch to direct-command probes only
- keep FSM work host-side: edit, compile, inspect
- do not attempt run/message-FSM actions until full runtime returns

## `run-fsm` fails immediately

Check in order:
1. connected?
2. lease held?
3. `supports_fsm_runtime` true?
4. module name matches underscore slug?
5. generated Python exists or can be auto-compiled?
6. does the module define the expected FSM class?

Asteria's loader does handle underscore module names -> CamelCase class names, so naming mismatch is less brittle than before.

## `send-text` or `send-speech` fails

Common causes:
- no active FSM
- active FSM not actually running
- minimal runtime fallback
- lease problem

Best response:
- re-read status
- confirm running FSM name and active flag
- if preserving the FSM no longer matters, unload and restart cleanly

## Stop behavior seems strange

Interpretation guide:
- `stop-all --keep-fsm` may leave a reactive FSM alive on purpose
- that is not automatically a bug
- if uncertainty remains, use `unload-fsm`

## Desk prompt stuck in `queued`, `failed`, or `not_sent`

Check in order:
1. the prompt's `forward_mode`
2. the prompt's `forward_status`, `forward_error`, and `forward_attempts`
3. if `forward_mode=openclaw`, inspect `status.bridge.*` and the prompt's `bridge_session_key`
4. if `forward_mode=codex`, inspect `status.codex_jobs` and `status.codex_timeout_minutes`

Response:
- if `forward_mode=queue`, treat the prompt as local-only and resolve it manually if appropriate
- if `forward_mode=openclaw` and the bridge is disabled or down, restart or let Asteria auto-start it, then use `retry-prompt-forward`
- if `forward_mode=codex` and a job is stuck, inspect the Codex output tail or kill the job from Debug before retrying manually
- if the prompt is still only `queued`, inspect activity log and the relevant worker state before assuming it is dead

## Prompt shows `sent` but is still pending

Meaning:
- the selected downstream worker started successfully
- Asteria has not yet seen a resolution come back

Response:
- do not treat `sent` as task completion
- inspect `forward_mode` before assuming which worker owns the prompt
- inspect the Desk activity feed and prompt log
- if `forward_mode=openclaw` and the prompt is old enough to be stale, retry forwarding or resolve it manually with an explicit response
- if `forward_mode=codex`, inspect `status.codex_jobs`, `get_codex_output`, or the Debug tab before killing/retrying it

## Codex prompt worker is running too long

Meaning:
- a `forward_mode=codex` prompt started a local `codex exec` worker
- the worker has not resolved the prompt yet

Response:
- inspect `status.codex_jobs` for the matching `prompt_id`
- read the recent output tail
- if the job is clearly wedged, kill it from the Debug tab or `kill_codex_job`
- if the work already completed out-of-band, resolve the prompt explicitly in Asteria instead of waiting forever

## Handheld says bridge live, but robot is offline

Meaning:
- the daemon/mobile surface is reachable
- the robot connection is not currently up

Response:
- read `/api/mobile/status` or normal `status`
- distinguish daemon reachability from robot reachability
- use reconnect only if lease/control ownership makes sense
- do not assume preview/Desk availability implies teleop availability

## Mobile preview missing

Common causes:
- no latest capture exists yet
- preview cache has not been generated yet
- the preview helper script/path is unavailable

Best response:
- capture a fresh image first
- retry the preview request
- inspect `asteria/artifacts/mobile-previews/` and the latest image metadata

## Compile/listing weirdness

Known area to watch:
- naming normalization and duplicate hyphen/underscore variants were cleaned up recently
- if a stale variant appears, prefer the canonical underscore slug and inspect the Asteria artifact FSM directory directly
