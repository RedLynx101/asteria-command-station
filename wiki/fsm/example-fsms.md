---
kind: operational
status: mixed
runtime:
  - host-side
  - aim_fsm_headless
last_reviewed: 2026-04-20
---

# Example FSMs

See also: [[fsm/fsm-authoring-patterns]], [[fsm/fsm-lifecycle]], [[open-questions]]

This page is a pattern library, not a promise that every file is safe to run live through Asteria unchanged.

## Highest-value starting examples

### Asteria-managed examples
- `asteria/artifacts/fsm/agent_smoke_test.fsm`
  - best validated no-motion probe
  - pattern: ready -> idle -> react to text/speech events
- `asteria/artifacts/fsm/agent_safe_observer.fsm`
  - validated no-motion follow-on probe
  - pattern: ready -> idle -> react to text/speech events with distinct acknowledgement speech
  - validated live in sequence after `agent_smoke_test` on 2026-04-15 in `aim_fsm_headless`
- `asteria/artifacts/fsm/asteria_demo.fsm`
  - tiny generated demo
  - pattern: say + short movement + turn + say
  - useful as a structure example, not as the first live test
- `asteria/artifacts/fsm/area_context_scan.fsm`
  - panoramic context-capture sweep
  - pattern: capture the starting view -> turn 90 degrees -> settle -> repeat until four headings are saved -> return to the original heading -> write a latest-run manifest
  - create/compile validated on 2026-04-15; intended output is `asteria/artifacts/images/area_context_scan/<timestamp>/` plus `asteria/artifacts/images/area_context_scan/latest_area_context_scan.json`
  - motionful example; run only from a safe live-control state because the sweep has not been live-validated yet
- `asteria/artifacts/fsm/scene_inventory_scan.fsm`
  - inventory-oriented context sweep for later agent reasoning
  - pattern: capture six headings in 60 degree increments -> save each image -> record visible world-map objects plus direct AI tag/cargo snapshots per view -> write an aggregate inventory manifest
  - create/compile validated on 2026-04-20; intended output is `asteria/artifacts/images/scene_inventory_scan/<timestamp>/` plus `asteria/artifacts/images/scene_inventory_scan/latest_scene_inventory_scan.json`
  - useful when Asteria needs a durable machine-readable scene summary rather than only a folder of images
- `asteria/artifacts/fsm/asteria_star_dance.fsm`
  - creative multi-step performance routine
  - pattern: spoken intro -> repeated forward/turn star path -> turn-based finale
  - motionful example created on 2026-04-15; keep human lease and a safe live-control state before running
- `asteria/artifacts/fsm/approach_operator_scan.fsm`
  - designated-operator approach helper
  - pattern: scan for the configured operator marker -> center it -> advance to a stand-off distance instead of driving all the way into contact
  - current default uses `AprilTag-0` as the operator-marker stand-in because that is the most validated live AprilTag surface in this workspace today
  - create/compile validated on 2026-04-20; the final forward step still depends on a visible world-map pose for the tag, so live behavior should be validated before depending on it operationally
- `asteria/artifacts/fsm/desk_mission_demo.fsm`
  - composed agent-facing mission demo
  - pattern: announce start -> run `scene_inventory_scan` -> read back a short spoken inventory summary from `latest_scene_inventory_scan.json` -> run `approach_operator_scan` -> announce completion
  - create/compile validated on 2026-04-20; useful as a top-level Asteria demo because it chains perception, durable artifact generation, host-readable summary, and a bounded follow-up action in one reusable entrypoint
- `asteria/artifacts/fsm/circle_10cm.fsm`
  - geometric locomotion example
  - pattern: approximate a 10 cm radius circle with repeated short forward segments and 30 degree turns
  - useful as a simple reusable movement-template reference
- `asteria/artifacts/fsm/follow_me_tag.fsm`
  - persistent AprilTag tracking demo
  - pattern: lock onto any visible AprilTag -> keep re-centering it -> if the tag disappears, run a bounded two-revolution scan until it is found again
  - create/compile validated on 2026-04-17
  - live-debugged on 2026-04-17: the original shared helper threw `'FollowAnyAprilTag' object has no attribute 'step_deg'` because its composite `StateNode` constructor used `setup()` before the tracking fields were initialized
  - after fixing the helper constructor order and restarting the daemon so the helper module was actually reloaded, `follow_me_tag` ran live without that attribute error and stayed active until manually unloaded
- `asteria/artifacts/fsm/get_mad.fsm`
  - dramatic barrel charge-and-kick demo
  - pattern: full-circle search for `BlueBarrel` or `OrangeBarrel` -> line up -> drive in -> hard kick
  - current shared helper now searches and recenters from AI vision as well as the world map, and the charge phase uses bounded AI-guided forward steps with `has_any_barrel()` hold checks instead of assuming the world map will always keep a visible barrel object
  - operator feedback on 2026-04-17 indicated the earlier world-map-only scan could miss a barrel that was visibly in frame during the rotation sweep
  - current source is host-validated after that fix; a fresh live rerun still needs to happen after the daemon picks up the updated helper module
- `asteria/artifacts/fsm/july4_celebration.fsm`
  - creative LED + speech + locomotion celebration routine
  - pattern: speech -> red/white/blue LED effects -> star-like path -> fireworks-style LED finale
  - motionful example created on 2026-04-15; create/compile is safe host-side, but live execution should be treated like any other movement FSM
- `asteria/artifacts/fsm/soccer_ball_pickup.fsm`
  - bounded soccer-ball acquisition routine
  - pattern: full-circle search for `Ball` / `SportsBall` -> path in -> touch pickup -> verify the robot is actually holding the ball
  - create/compile validated on 2026-04-16
  - live retest note from 2026-04-16: a close-up camera frame showed the soccer ball sitting at the very bottom foreground while `PickUp(...)` was still active, so visible contact is not the same thing as a completed pickup node
  - intended for the magnetic front pickup case; failure speech distinguishes "could not find the ball" from "touched it but did not secure it"
- `asteria/artifacts/fsm/soccer_tag0_shot.fsm`
  - bounded held-ball shot routine for the home setup
  - pattern: require a held soccer ball -> full-circle tag search with direct AI-vision fallback -> aim using world-map bearing when available and AI-vision centering otherwise -> hard kick
  - current source was updated after live feedback on 2026-04-16 because the split-search version did not reliably reacquire `AprilTag-0` while spinning/turning in the home bowling setup
  - an earlier combined ball-to-tag version was live-run validated on 2026-04-16; the current split-search helper is compile-validated and incorporates the newer AI-vision-assisted tag search/aim fix
  - uses the daemon-visible tag object name `AprilTag-0`
- `asteria/artifacts/fsm/tag_gallery_tour.fsm`
  - AprilTag narration and centering tour
  - pattern: search for AprilTags `0..4` one at a time -> center each one if found -> speak the result -> continue
  - create/compile validated on 2026-04-17
  - shared-helper note: `GalleryStop` had the same composite `StateNode` constructor-order bug as `FollowAnyAprilTag` and was patched in the same pass before any live run
- `asteria/artifacts/fsm/soccer_bowling_round.fsm`
  - composed bowling-round orchestration example
  - pattern: acquire the soccer ball -> announce the shot phase -> search for `AprilTag-0` -> hard kick
  - create/compile validated on 2026-04-16
  - intended as the reusable one-command wrapper around the ball-pickup and tag-shot subroutines
- `asteria/artifacts/fsm/openclaw_probe.fsm`
- `asteria/artifacts/fsm/test_agent_flow.fsm`
  - small generated probes following the same simple sequence style

## Conversational / GPT-command patterns

### `vex-aim-tools/GPT_test.fsm`
Most expressive command-dispatch example in the repo.

Useful ideas:
- command language returned by an LLM
- dispatch loop over `#forward`, `#turn`, `#doorpass`, `#pickup`, `#glow`, `#flash`, `#camera`
- fallback prompt when actions fail

Caution:
- broad action surface
- relies on many AIM features and assumptions
- better as a design reference than a first live Asteria program

### `lab2/Sashay_clean.fsm` and `lab2/Sashay_test.fsm`
A leaner conversational command loop.

Useful ideas:
- parse model output into robot commands
- wrap plain text into `#say`
- dispatch simple locomotion commands

## Vision / classification patterns

### `lab3/ThumbsUp.fsm`
- sends the current camera image to GPT
- asks a narrow yes/no question
- branches to success/failure behavior

Good template for low-bandwidth perception decisions.

### `lab6/Lab6c.fsm`
- runs a custom barrel detector on camera frames
- annotates detections
- prints/report loop on demand

Good template for camera-processing hooks and reporting.

### `lab7/DominoRealTime.fsm`, `lab7/DominoYOLO.fsm`, `lab7/DominoClassifier.fsm`, `lab7/MobileNet.fsm`, `lab8/DominoSegment.fsm`
- vision-heavy examples
- object/detector/classifier loops
- likely depend on local model files or specialized environment setup

Treat these as perception architecture references.

## Navigation / world-model patterns

### `lab5/ThroughTheDoor.fsm`
- finds visible doorways from the world map
- prefers marker-defined doorways when present
- uses `DoorPass()`

Great reference for world-map selection logic and doorway behavior.

### `lab6/Lab6b.fsm`
- selects a world-map object and uses `PilotToPose()`
- shows a minimal pilot loop gated by a text-message trigger

### `vex-aim-tools/aim_fsm/pilot.fsm`
- older but useful navigation reference
- includes `PilotToPose()` and `DoorPass()` style patterns

## Game / task orchestration patterns

### `lab5/Nim.fsm`
Large multi-state task program.

Useful ideas:
- internal game state
- alternating turns
- pick up / drop / return-home subflows
- mix of speech, world state, and manipulation logic

This is a strong example of when an FSM is justified because direct commands would be too brittle.

## Kinematics / frame / calibration helpers

- `lab4/Q8DisplayFrameTest.fsm`: display-frame inspection helper
- `lab4/Q10LedPromptHelper.fsm`: prompt helper for LED behavior work through `GPT_test`
- `lab4/Q6CameraOrigin.fsm`, `lab4/Q7FruitFly.fsm`, `lab4/Q9WheelFrameTest.fsm`, `lab4/calibrate.fsm`: lab-specific calibration and geometry references

## Quick inventory by category

### Asteria artifact FSMs
- `agent_smoke_test.fsm`
- `agent_safe_observer.fsm`
- `area_context_scan.fsm`
- `approach_operator_scan.fsm`
- `asteria_demo.fsm`
- `asteria_star_dance.fsm`
- `circle_10cm.fsm`
- `desk_mission_demo.fsm`
- `follow_me_tag.fsm`
- `get_mad.fsm`
- `july4_celebration.fsm`
- `scene_inventory_scan.fsm`
- `soccer_ball_pickup.fsm`
- `soccer_bowling_round.fsm`
- `soccer_tag0_shot.fsm`
- `tag_gallery_tour.fsm`
- `openclaw_probe.fsm`
- `test_agent_flow.fsm`

### Early locomotion / simple demos
- `lab2/Example1.fsm`
- `lab2/TickToc.fsm`
- `projects/openclaw-vex-aim/skills/openclaw-vex-aim/templates/basic.fsm`

### GPT / dialogue / command language
- `lab2/Sashay_clean.fsm`
- `lab2/Sashay_test.fsm`
- `vex-aim-tools/GPT_test.fsm`

### Object, marker, or world-map driven
- `lab2/Fanta.fsm`
- `lab3/Confidence.fsm`
- `lab3/Object_test.fsm`
- `lab3/TurnToClosest.fsm`
- `lab3/TwoMarkers.fsm`
- `lab5/Nim.fsm`
- `lab5/ThroughTheDoor.fsm`
- `lab6/Lab6a.fsm`
- `lab6/Lab6b.fsm`
- `vex-aim-tools/aim_fsm/pilot.fsm`
- `vex-aim-tools/aim_fsm/pickup.fsm`

### Vision-heavy / ML-heavy
- `lab3/ThumbsUp.fsm`
- `lab6/Lab6c.fsm`
- `lab6/submissionLab6_nhicks/Lab6c.fsm`
- `lab7/DominoClassifier.fsm`
- `lab7/DominoRealTime.fsm`
- `lab7/DominoYOLO.fsm`
- `lab7/MobileNet.fsm`
- `lab8/DominoSegment.fsm`

## My recommendation for future reuse

Start from this ladder:
1. `agent_smoke_test`
2. `ThumbsUp` for narrow perception branching
3. `ThroughTheDoor` for structured world-model navigation ideas
4. `GPT_test` only after the robot control plane is already trusted and bounded
