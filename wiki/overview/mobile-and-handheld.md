---
kind: operational
status: mixed
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
  - host-side
last_reviewed: 2026-04-15
---

# Mobile And Handheld

See also: [[overview/stack-map]], [[overview/command-surface]], [[overview/control-and-leases]], [[procedures/recovery-playbooks]], [[sources/mobile-runtime-surface]]

## What this surface is

The mobile surface is a bearer-authenticated client layer mounted into the same Asteria daemon.

It currently serves:
- status/bootstrap reads
- Desk prompt submission
- teleop claim/release
- teleop vector and direct teleop commands
- latest image access and cached preview generation
- legacy local session storage for a mobile chat API shape

The old-3DS client in `apps/asteria-ds/` is the main concrete handheld consumer in this repo right now.

## What the 3DS client actually does now

### Chat tab
- sends directly to `POST /api/mobile/prompt`
- is a Desk prompt surface, not a live mobile agent-worker chat loop
- shows local transcript UI around Desk submissions and results

### Pilot tab
- claims/releases the Asteria lease through the mobile bridge
- exposes reconnect, capture, kick, stop, and directional teleop actions
- fetches the latest cached preview for the top screen

## Teleop model

Current runtime-adapter behavior:
- forward/strafe vectors map to `drive_at`
- turn vectors map to `turn_at`
- low-magnitude inputs are rate-limited or ignored as deadzone noise
- releasing teleop sends `stop_all` with `stop_fsm=false`

That means the handheld stop path is intentionally "stop motion only" so it does not unload an active FSM just because the operator lets go of the stick or touch pad.

## Command truth versus labels

Important current command semantics:
- `grab_assist` from the mobile surface is a soft-kick fallback, not a true object-aware pickup routine
- `place` is explicitly unsupported as a direct mobile bridge action
- `capture_image` still goes through the normal daemon capture path

## Image preview path

The handheld preview route is not the same as the desktop image path.

Current path:
- Asteria keeps the latest full capture metadata
- mobile preview requests hit `/api/mobile/images/preview`
- the bridge generates or reuses a cached `rgb565` preview file
- the 3DS draws that preview directly instead of decoding JPEGs on-device

## Auth and identity

The mobile layer expects:
- bearer token auth from `asteria/artifacts/mobile-config/mobile-auth.json`
- per-device holder metadata such as `holder_id` and `holder_label`

The runtime adapter currently presents the handheld as a human holder by default, which matters for lease behavior and for how mobile claims interact with agent control.

## Validated anchors from current workspace notes

The current notes indicate these were verified on 2026-04-14:
- `/api/mobile/status`
- `/api/mobile/images/preview`
- `/api/mobile/teleop/claim`
- `/api/mobile/teleop/command`
- live 3DS redeploy using the current config/token path

## Remaining caveats

- Legacy `/api/mobile/chat/sessions` storage still exists, but there is no validated autonomous worker loop behind it.
- The 3DS client is the best documented consumer; other mobile clients should not assume a richer chat-worker backend than the code actually provides.
- Any live teleop still depends on normal connection state and lease discipline.
