---
kind: operational
status: validated
runtime:
  - host-side
last_reviewed: 2026-04-15
---

# Desk Prompt Routing

See also: [[overview/command-surface]], [[overview/stack-map]], [[procedures/recovery-playbooks]], [[sources/openclaw-direct-bridge]], [[sources/runtime-prompt-flow]]

## Canonical model

The Asteria Desk is canonical.

That means:
- prompt creation happens in Asteria first
- prompt persistence in `prompt-log.json` is the durable source of truth
- downstream execution modes are follow-on steps, not the source of record

## Current lifecycle

1. `submit_prompt` creates a local prompt entry and activity item.
2. The prompt records a `forward_mode`: `queue`, `openclaw`, or `codex`.
3. `queue` leaves the prompt local-only with `forward_status=not_sent`.
4. `openclaw` assigns a prompt-specific session key and queues background Gateway forwarding.
5. `codex` queues a background local `codex exec` worker tracked by the daemon.
6. A downstream worker starting or accepting the run flips the prompt to `forward_status=sent`.
7. Later, prompt resolution changes prompt `status` from `pending` to `resolved`.

## Status fields that matter

Prompt state and bridge state are intentionally separate.

### Prompt `forward_mode`
- `queue`
- `openclaw`
- `codex`

### Prompt `status`
- `pending`
- `resolved`

### Prompt `forward_status`
- `not_sent`
  Local-only queue mode or no successful downstream handoff yet.
- `queued`
  Background downstream work is pending.
- `retrying`
  A retry/backoff pass is in flight for the OpenClaw worker path.
- `sent`
  The selected downstream worker accepted or started the run.
- `failed`
  Asteria attempted a downstream worker path and it failed before completion.

### Other useful prompt metadata
- `forward_error`
- `forward_attempts`
- `forwarded_at`
- `bridge_session_key`

## Acceptance versus completion

Do not conflate these:
- `forward_status=sent` means a downstream worker started successfully
- prompt `status=resolved` means someone later closed it out back in Asteria

That split is deliberate. It prevents Asteria from treating a successful bridge handoff as if the actual task were already finished.

Mode-specific meaning:
- in `openclaw`, `sent` means OpenClaw accepted the turn
- in `codex`, `sent` means the local Codex process was started
- in `queue`, prompts normally stay `not_sent`

## Session routing

The validated local routing pattern is:
- base session key: `session:asteria-desk`
- default template: `{base_session_key}:{prompt_id}`
- resulting session example: `session:asteria-desk:prompt-1234abcd`

Session routing is carried in the `X-OpenClaw-Session-Key` header, not a JSON `session_key` field.

The prompt-specific template matters because it avoids serializing unrelated Desk prompts behind one long-lived shared OpenClaw session.

## Reliability behavior

Current code/runtime behavior:
- all prompt modes persist locally first
- `openclaw` mode is queue-first and durable locally
- if Gateway `/health` is down, Asteria can attempt `openclaw gateway` auto-start
- unresolved non-`sent` OpenClaw prompts are retried with backoff
- older unresolved `sent` OpenClaw prompts can be treated as stale and retried after restart
- `retry-prompt-forward` is the manual recovery tool for OpenClaw mode when config or Gateway state changes
- `codex` mode tracks live workers in `status.codex_jobs`, times them out with `codex_timeout_minutes`, and can be interrupted with `kill_codex_job`

## Fastest inspection points

Check these first:
- `status.bridge`
- `status.codex_jobs`
- `status.codex_timeout_minutes`
- `status.latest_pending_prompt`
- `status.prompts`
- `status.activities`

For CLI recovery:
- `python -m asteria.cli list-prompts --pending-only --limit 10`
- `python -m asteria.cli retry-prompt-forward --prompt-id <id>`
- `python -m asteria.cli resolve-prompt --prompt-id <id> --response "..."`

## Practical rule

- Treat prompt persistence as the hard guarantee.
- Treat `openclaw` and `codex` as optional worker modes layered on top of that guarantee.
- If a prompt is still pending, inspect its `forward_mode` and `forward_status` before assuming the wrong worker path broke.
