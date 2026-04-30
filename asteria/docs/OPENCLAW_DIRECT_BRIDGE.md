# OpenClaw Direct Bridge

This document describes the direct Asteria Desk -> OpenClaw prompt bridge.

## Intent

- Asteria remains the source of truth for Desk prompts.
- OpenClaw is the worker that should wake up immediately when Desk prompts arrive.
- Heartbeat polling remains the fallback path when the direct bridge is disabled or broken.

## Runtime behavior

On `submit_prompt`, the daemon now:

1. creates the local prompt entry and persists it
2. queues background forwarding work instead of blocking the Desk submit path on a full OpenClaw turn
3. records per-prompt forward metadata
4. retries failed or stale unresolved forwards from the persisted prompt log
5. exposes that state through `/api/status`, `list-prompts`, and the Desk tab

Prompt forward fields:

- `forward_status`
- `forwarded_at`
- `forward_error`
- `forward_attempts`
- `bridge_session_key`

## Validated local configuration

The currently validated local bridge settings are:

- `ASTERIA_OPENCLAW_BRIDGE_ENABLED=true`
- `ASTERIA_OPENCLAW_GATEWAY_URL=http://127.0.0.1:18889`
- `ASTERIA_OPENCLAW_GATEWAY_PATH=/v1/responses`
- `ASTERIA_OPENCLAW_SESSION_KEY=session:asteria-desk`
- `ASTERIA_OPENCLAW_SESSION_KEY_TEMPLATE={base_session_key}:{prompt_id}`
- `ASTERIA_OPENCLAW_BRIDGE_TIMEOUT_MS=120000`
- `ASTERIA_OPENCLAW_BRIDGE_MODEL=openclaw/default`
- `ASTERIA_OPENCLAW_BRIDGE_USER=asteria-desk-bridge`
- `ASTERIA_OPENCLAW_AUTO_START=true`

The local OpenClaw Gateway must also have `gateway.http.endpoints.responses.enabled=true` and a valid bearer token configured for Asteria.

## Wire format notes

- Session routing is passed through the `X-OpenClaw-Session-Key` header.
- Do not send `session_key` in the JSON body. OpenClaw rejects that payload.
- The bridge now uses the Gateway streaming responses surface and treats the first OpenClaw acceptance event as the success boundary for forwarding.
- A prompt flips to `forward_status=sent` as soon as OpenClaw accepts the turn, even if the actual agent work has not finished yet.
- The Desk submit path no longer waits for that completion. The prompt is queued locally first, then forwarded in the background.
- Prompt resolution is separate from bridge acceptance. A prompt can remain `pending` in Asteria while already showing `forward_status=sent`.
- If OpenClaw later resolves the prompt in Asteria, the prompt status becomes `resolved`.
- If the OpenClaw turn fails after acceptance, Asteria keeps the prompt marked as forwarded and logs the run error as activity instead of pretending the bridge itself failed.
- By default, Asteria now expands the base session key into a prompt-specific session key such as `session:asteria-desk:prompt-1234abcd`. That prevents one older Asteria Desk turn from serializing later prompts behind the same long-lived OpenClaw session.
- If the local Gateway is down, Asteria now attempts to start it with `openclaw gateway` and waits briefly for `/health` before giving up.

## Current behavior

The loopback Gateway on this machine has been verified to accept `POST /v1/responses`, and Asteria can now:

- store the Desk prompt locally first
- mark it as forwarded as soon as OpenClaw accepts the turn
- keep prompt resolution independent from transport success

Asteria still treats forwarding as best-effort:

- local prompt creation still succeeds if the gateway is down or misconfigured
- Desk cards show whether the prompt was queued, forwarded, failed, or stayed local-only
- failed forwards back off and retry from the persisted queue
- unresolved stale `sent` prompts can be retried after restart instead of hanging forever
- `retry-prompt-forward` can be used after gateway configuration changes

## CLI

Useful commands:

```powershell
python -m asteria.cli status
python -m asteria.cli list-prompts --pending-only --limit 10
python -m asteria.cli retry-prompt-forward --prompt-id prompt-1234abcd
python -m asteria.cli resolve-prompt --prompt-id prompt-1234abcd --response "Handled"
```
