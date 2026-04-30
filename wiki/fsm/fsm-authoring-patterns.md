---
kind: operational
status: mixed
runtime:
  - host-side
  - aim_fsm_headless
last_reviewed: 2026-04-20
---

# FSM Authoring Patterns

See also: [[fsm/fsm-lifecycle]], [[fsm/example-fsms]], [[robot/safety-and-stop-semantics]]

## Best current authoring baseline

Use a no-motion event-capable FSM first, then scale up.

`agent_smoke_test` is the best validated template because it demonstrates:
- `Say(...)`
- idle waiting
- text event handling
- speech event handling
- no meaningful motion requirement

## Pattern 1: no-motion smoke test

Use when validating the stack itself.

Shape:
- announce ready
- idle state
- accept text and speech events
- announce completion or react with simple output

Why it matters:
- proves the daemon can load and run an FSM
- proves event injection works
- avoids unsafe movement while testing control-plane assumptions

## Pattern 2: direct command replacement threshold

Keep behavior as direct commands if it is only one bounded action.

Promote to FSM when the behavior needs:
- branching
- loops
- event handling
- reusable state
- autonomous retries

## Pattern 3: perception-to-action loop

Seen in files like `ThumbsUp.fsm`, `ThroughTheDoor.fsm`, and `Lab6c.fsm`.

Common structure:
1. sense world or camera input
2. interpret or classify it
3. choose one next action
4. loop or retry on failure

## Pattern 4: command-dispatch conversational FSM

Seen strongly in `GPT_test.fsm` and `Sashay_clean.fsm`.

Shape:
- hear prompt
- ask model
- parse returned command lines
- dispatch each command node in sequence
- fall back to speech/text when the response is not a command program

This is powerful, but it is not the right first live pattern for Asteria. It belongs after the control plane is already trusted.

## Pattern 5: navigation/world-map FSM

Seen in `ThroughTheDoor.fsm`, `Lab6b.fsm`, `pilot.fsm`, `Nim.fsm`.

These rely on higher-level AIM concepts such as:
- world-map objects
- pathing or pilot nodes
- doorway/object semantics
- localization assumptions

Use these as pattern references, not as immediate drop-in live programs.

Current repo-grounded notes:
- the live world map creates AprilTag objects for ids `0..4` with names like `AprilTag-0`, even though the older `Tagdesc` docstring still says ids should be positive and not `0`
- `ObjectSpecNode`-based nodes such as `PickUp` and `TurnToward` work best with world-object ids, regexes, concrete `WorldObject` instances, or `WorldObject` subclasses
- direct AI-vision snapshots can still matter even when the world map exists, because the home bowling setup exposed cases where `AprilTag-0` was visible enough for live play but not reacquired reliably by a pure world-map-visible spin search

### Small-angle turn guard

When a target is already almost centered, a raw `TurnToward(...)` can request such a small turn that the drive actuator never reports a real turn start. In that case the node may not complete cleanly.

Use a wrapper that:
- computes the target angle first
- immediately completes when the absolute angle is below a small threshold
- only dispatches a drive turn when a real turn is actually needed

Current repo example:
- `soccer_tag0_shot.fsm`
- the baseline ball-to-tag routine was live validated on 2026-04-16
- the current small-angle guard revision was compile-validated after review, but not separately re-live-validated in this session

## Pattern 6: persisted area-context sweep

Use when the robot needs a small durable visual memory bank for later host-side review.

Shape:
1. prepare a deterministic artifact directory for the run
2. wait for a fresh frame before the first capture
3. save one image per heading
4. insert a short settle delay after each 90 degree turn before the next capture
5. write a manifest that points to the latest run directory and its image files
6. return the robot to its original heading before finishing

Why it matters:
- later Asteria work can inspect the saved files without keeping the FSM running
- stable filenames and manifests are easier to consume than ad hoc snapshots
- settle delays reduce the chance of saving a stale or motion-blurred frame right after a turn

Current repo example:
- `area_context_scan.fsm`
- create/compile validated on 2026-04-15
- intended image source is `robot.world.latest_image.raw_image`
- live motionful execution still needs its own validation pass before treating this pattern as fully validated

Inventory-oriented variant:
- `scene_inventory_scan.fsm`
- create/compile validated on 2026-04-20
- extends the same persisted-scan structure with per-view world-map summaries and direct AI tag/cargo snapshots
- useful when later host-side work needs a machine-readable scene inventory instead of only saved JPEGs

## Pattern 7: split search, pickup, and shot routines

Use when the task needs bounded search behavior, but you still want the pickup, shot, and orchestration stages to stay reusable.

Shape:
1. full-circle search in fixed turn increments for the target world object
2. branch immediately with spoken failure if the sweep finishes without a visible match
3. keep pickup and shot as separate subroutines so a composed task can reuse them
4. verify the robot is actually holding the ball before starting the shot phase
5. search for `AprilTag-0` with a direct AI-vision fallback instead of trusting a world-map-only spin search
6. aim with a small-angle completion guard and an AI-vision centering fallback when the world-map tag object drops out
7. kick with the explicitly chosen kick strength

Why it matters:
- avoids baking ball acquisition into every shot routine
- keeps search behavior bounded and easy to reason about
- makes "already holding the ball" versus "need to go get the ball first" explicit
- lets a higher-level game FSM orchestrate the round without duplicating low-level search logic

Current repo example:
- `soccer_search_nodes.py`
- `soccer_ball_pickup.fsm`
- `soccer_tag0_shot.fsm`
- `soccer_bowling_round.fsm`
- all of the current split routines were create/compile validated on 2026-04-16
- the earlier combined `soccer_tag0_shot.fsm` variant was live-run validated before this split refactor
- live knowledge worth keeping:
  - `robot0.has_ball()` only recognizes AI classname `Ball`, so soccer hold checks should explicitly accept both `Ball` and `SportsBall`
  - a 2026-04-16 retest captured the soccer ball visibly pressed against the lower foreground while `PickUp(BALL_SPEC)` was still active, so post-pickup hold verification is still necessary even when contact looks correct
  - the split `soccer_tag0_shot` helper needed an AI-vision-assisted `AprilTag-0` search/aim update after operator feedback that the robot was not reacquiring the tag reliably while spinning and turning to face it

## Pattern 8: bounded reacquisition tracking

Use when a demo should keep following a visual target, but only for a bounded amount of blind searching when the target drops out of view.

Shape:
1. acquire any visible target that matches the desired class
2. keep re-centering it with short aim corrections while it stays visible
3. if the target disappears, switch into a circular scan instead of failing immediately
4. keep the scan budget explicit, such as two full revolutions
5. fail loudly once the budget is exhausted instead of spinning forever

Why it matters:
- gives a demo a more "alive" feel than one-shot target acquisition
- avoids unbounded spinning when the operator walks the target out of frame
- separates ordinary tracking from the more expensive reacquisition behavior

Current repo example:
- `follow_me_tag.fsm`
- the reacquisition scan is capped at two 360 degree revolutions before the routine gives up
- live debug on 2026-04-17 exposed a concrete constructor-order pitfall in the shared helper node `FollowAnyAprilTag`
- after fixing that helper and restarting the daemon, `follow_me_tag` ran live without the earlier `'FollowAnyAprilTag' object has no attribute 'step_deg'` failure and stayed active until manual unload

## Pattern 9: composite StateNode constructor rule

Use when a reusable helper node builds its child graph inside `setup()`.

Shape:
1. assign every instance attribute that `setup()` depends on before calling `super().__init__()`
2. remember that `aim_fsm.base.StateNode.__init__()` calls `setup()` immediately
3. if a generated FSM imports a shared helper module, restart the daemon after helper edits before trusting a live rerun

Why it matters:
- a composite helper can fail before the FSM even starts if `setup()` touches fields that have not been initialized yet
- the traceback can look confusing after a source edit because the daemon may still be running an older cached helper module
- reloading only the entry FSM module is not enough when the real fix lives in an imported helper

Current repo examples:
- `asteria/artifacts/fsm/asteria_demo_nodes.py`
- `FollowAnyAprilTag` and `GalleryStop` both needed this fix on 2026-04-17
- the daemon currently reloads the entry FSM module on `run_fsm`, but imported helper modules may still require a daemon restart to pick up edits reliably during live debugging
- the same daemon-restart caveat applies to shared helper fixes for `get_mad`, because its barrel behavior also lives in `asteria_demo_nodes.py`

## Pattern 10: AI-vision fallback for model objects

Use when the target is an AI model object such as a barrel or ball and the live world map may lag behind what the camera is already seeing.

Shape:
1. prefer a visible world-map object when it exists, because it gives you a geometric pose
2. fall back to direct AI vision when the camera clearly sees the object but the world map does not expose it as visible yet
3. keep the AI fallback explicit in search, centering, and the final close-in approach
4. use the robot's built-in held-object checks when they exist instead of guessing from contact alone

Why it matters:
- model-object detection can be visibly correct in the camera while still being absent from the world-map-visible path used by generic `ObjectSpecNode` helpers
- a world-map-only scan can falsely report failure even after the robot has looked straight at the target
- the close-in phase is more reliable when it checks `has_any_barrel()` or the equivalent held-object signal instead of assuming one forward move guarantees contact

Current repo example:
- `asteria/artifacts/fsm/get_mad.fsm`
- shared helper logic in `asteria/artifacts/fsm/asteria_demo_nodes.py`
- the current barrel path was revised on 2026-04-17 after operator feedback that the earlier world-map-only sweep could miss a barrel that was visibly in frame

## Pattern 11: designated-tag stand-off approach

Use when Asteria should move closer to a known marker or operator, but should still stop short instead of colliding with the target or stand.

Shape:
1. scan for a designated AprilTag with the same bounded search logic used elsewhere
2. center it with world-map bearing when possible and AI centering when needed
3. only attempt the forward approach when the tag has a visible world-map pose
4. stop at a configurable stand-off distance rather than driving to direct contact
5. fail explicitly if the marker can be seen but not ranged safely enough for the final forward leg

Why it matters:
- gives the agent a reusable “come closer to the person / marker” behavior without hard-coding a collision path
- keeps the search and centering behavior consistent with the validated AprilTag helpers already used in other Asteria FSMs
- makes the safety boundary explicit: the final forward leg still relies on a geometric world-map pose, not on blind camera-only movement

Current repo example:
- `asteria/artifacts/fsm/approach_operator_scan.fsm`
- shared helper logic in `asteria/artifacts/fsm/asteria_demo_nodes.py`
- create/compile validated on 2026-04-20
- current default uses `AprilTag-0` as the operator-marker stand-in because that is the most validated live tag target in this workspace today
- live validation is still needed before treating this as a dependable handoff or operator-approach behavior

## Pattern 12: composed agent mission wrapper

Use when Asteria needs one reusable top-level FSM that ties together perception, artifact creation, a spoken summary, and a bounded follow-up action.

Shape:
1. start with a short spoken announcement so the operator knows the mission began
2. run a lower-level scan FSM that writes durable artifacts and a latest-run manifest
3. read the manifest back inside a small helper node and convert the machine-readable result into a concise spoken summary
4. hand off to a second reusable action FSM instead of duplicating its search/approach logic
5. end with an explicit success or failure announcement

Why it matters:
- keeps higher-level Asteria demos readable instead of burying all logic in one giant helper module
- reuses already-validated subflows like `scene_inventory_scan` and `approach_operator_scan`
- makes the durable artifact path part of the behavior contract, so later host-side reasoning can inspect the same manifest the robot summarized out loud

Current repo example:
- `asteria/artifacts/fsm/desk_mission_demo.fsm`
- create/compile validated on 2026-04-20
- current summary logic reads `asteria/artifacts/images/scene_inventory_scan/latest_scene_inventory_scan.json` and speaks a compact report of mapped objects, visible tag ids, and cargo classes before the operator-approach phase begins
- because this top-level mission composes imported helper modules and child FSM modules, live reruns should follow the usual daemon-restart rule if those shared helpers were edited in the current daemon process

## Naming and module/class alignment

Asteria’s loader resolves underscore module names to CamelCase classes.

Examples:
- `agent_smoke_test.fsm` -> `AgentSmokeTest`
- `asteria_demo.fsm` -> `AsteriaDemo`

This alignment is important when importing generated modules and when interpreting older examples.

## Authoring rules I should follow

- start from the simplest validated pattern that answers the question
- keep first live probes non-motion
- assume `aim_raw_minimal` may appear and gate FSM plans on `supports_fsm_runtime`
- make stop behavior explicit in the surrounding procedure
- store reusable examples under the Asteria artifact FSM area, not scattered ad hoc
