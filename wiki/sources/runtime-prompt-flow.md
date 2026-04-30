---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_files:
  - asteria/daemon/runtime.py
  - asteria/openclaw_bridge.py
---

# Source Summary: Runtime Prompt Flow

## Key points extracted

- `submit_prompt` creates the prompt locally first and records a `forward_mode` of `queue`, `openclaw`, or `codex`.
- prompts always persist locally before any downstream worker path starts.
- Prompt forward state is persisted on the prompt entry itself through `forward_status`, `forward_error`, `forward_attempts`, `forwarded_at`, and `bridge_session_key`.
- The runtime exposes bridge state through `status.bridge`, including endpoint, health URL, last attempt, last error, and last response id.
- The runtime also exposes background Codex workers through `status.codex_jobs` and `status.codex_timeout_minutes`.
- OpenClaw prompts can be retried automatically when unresolved and not truly forwarded, and older unresolved `sent` prompts can be treated as stale for retry.
- For `openclaw`, the bridge client treats OpenClaw acceptance as the success boundary for forwarding and watches streaming response events to detect that acceptance.
- For `codex`, `sent` means the local Codex process was started; later prompt resolution is still separate.
- OpenClaw session routing defaults to prompt-scoped session keys, which avoids serializing multiple Desk prompts onto one shared OpenClaw session.

## Wiki pages fed by this source

- [[overview/desk-prompt-bridge]]
- [[overview/command-surface]]
- [[procedures/recovery-playbooks]]
