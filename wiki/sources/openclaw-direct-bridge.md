---
kind: source-summary
status: validated
last_reviewed: 2026-04-15
source_file: asteria/docs/OPENCLAW_DIRECT_BRIDGE.md
---

# Source Summary: OpenClaw Direct Bridge

## Key points extracted

- This source is specifically about `forward_mode=openclaw`, not the full Desk routing model.
- Desk prompts are persisted in Asteria first and only then forwarded into OpenClaw.
- The submit path is queue-first; Asteria no longer blocks prompt submission on a full OpenClaw turn.
- The validated local bridge path is OpenClaw Gateway `POST /v1/responses` on `http://127.0.0.1:18889`.
- Session routing belongs in the `X-OpenClaw-Session-Key` header, not in a JSON `session_key` body field.
- Prompt-specific session keys are the current default through `{base_session_key}:{prompt_id}`.
- `forward_status=sent` means OpenClaw accepted the turn; prompt resolution is a separate later event in Asteria.
- The bridge is intentionally best-effort: local prompt storage still succeeds even if forwarding fails.
- Asteria can auto-start the local Gateway and retry failed/stale forwards from the persisted prompt queue.
- `retry-prompt-forward` remains the recovery path after configuration or availability issues.

## Wiki pages fed by this source

- [[overview/desk-prompt-bridge]]
- [[overview/stack-map]]
- [[overview/command-surface]]
- [[procedures/recovery-playbooks]]
