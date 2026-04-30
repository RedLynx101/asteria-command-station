---
kind: operational
status: mixed
runtime:
  - aim_fsm_headless
  - aim_raw_minimal
last_reviewed: 2026-04-15
---

# Capability Matrix

See also: [[overview/runtime-modes]], [[fsm/fsm-lifecycle]], [[robot/safety-and-stop-semantics]]

## Reading this page

- **Validated** means observed in current live Asteria notes.
- **Code-defined** means present in current daemon/CLI code, but not all of it has been revalidated live in this wiki pass.

| Capability                               | Host-side only | `aim_fsm_headless` |             `aim_raw_minimal` | Confidence                                              |
| ---------------------------------------- | -------------- | -----------------: | ----------------------------: | ------------------------------------------------------- |
| Status / telemetry                       | no             |                yes |                           yes | validated                                               |
| Configure connection target              | yes            |                n/a |                           n/a | code-defined                                            |
| Create FSM source                        | yes            |                n/a |                           n/a | validated                                               |
| Compile FSM source                       | yes            |                n/a |                           n/a | validated                                               |
| Run FSM live                             | no             |                yes |                            no | validated                                               |
| Send text event to active FSM            | no             |                yes |                            no | validated                                               |
| Send speech event to active FSM          | no             |                yes |                            no | validated                                               |
| Unload active FSM                        | no             |                yes | no meaningful active FSM path | validated                                               |
| Stop all, unload FSM                     | no             |                yes |                           yes | validated for full runtime, code-defined generally      |
| Stop all, keep FSM loaded                | no             |                yes |                 limited value | validated for full runtime                              |
| Capture image                            | no             |                yes |                           yes | validated                                               |
| Display screen text (`say`)              | no             |                yes |                           yes | validated                                               |
| Kick                                     | no             |                yes |                           yes | code-defined                                            |
| Discrete move / turn / sideways          | no             |                yes |                           yes | code-defined, movement intentionally not re-tested here |
| Continuous `drive_at` / `turn_at` teleop | no             |                yes |                           yes | code-defined, validated in handheld path and desktop surface wiring |
| FSM auto-compile before run              | partly         |                yes |                           n/a | code-defined plus workflow notes                        |
| Mobile bridge status / prompt / teleop surface | n/a       |                yes |                           yes | code-defined with validated 3DS path                    |
| Cached mobile preview route (`/api/mobile/images/preview`) | n/a |                yes |                           yes | validated in current handheld path                      |

## Most important decision split

### Use direct commands when
- you are probing connectivity or display/camera behavior
- you are in `aim_raw_minimal`
- the task is one bounded action
- you need the safest possible recovery path

### Use FSMs when
- the task is multi-step
- the task is event-driven
- the behavior should be reusable
- `supports_fsm_runtime` is true

## Current validated live anchors

On 2026-04-14, the live stack validated:
- image capture
- screen text
- live `agent_smoke_test`
- text and speech event injection
- `stop-all --keep-fsm`
- `unload-fsm`

Those are the strongest current operational anchors for future work.

## Additional control-plane notes

- Mobile teleop vectors now map into `drive_at` / `turn_at` rather than only discrete fixed-distance step commands.
- The desktop Operations view now exposes both discrete step commands and an optional continuous hold mode that uses the same `drive_at` / `turn_at` path.
- The mobile stop path intentionally uses `stop_all` with `stop_fsm=false`, so releasing handheld control does not unload an active FSM by default.
- Mobile prompt submission is a Desk path first; legacy session storage still exists, but it is not the same thing as a validated mobile worker loop.
