---
kind: hub
status: validated
runtime:
  - host-side
  - aim_fsm_headless
last_reviewed: 2026-04-15
---

# FSM Lifecycle

See also: [[overview/runtime-modes]], [[robot/capability-matrix]], [[fsm/fsm-authoring-patterns]], [[procedures/live-probe-checklist]]

## The lifecycle

1. create source `.fsm`
2. compile to generated Python
3. connect in a runtime that supports FSMs
4. run the compiled module
5. inject events if needed
6. stop or unload intentionally
7. keep artifacts and notes

## File locations

Asteria-managed FSM files live in:
- source: `asteria/artifacts/fsm/<name>.fsm`
- generated: `asteria/artifacts/fsm/<name>.py`

Run/compile artifacts go under `asteria/artifacts/runs/`.

## Naming rules

`asteria/tools/fsm.py` normalizes names with `slugify()`:
- non-alphanumeric separators become underscores
- the generated class name is CamelCase via `class_name_for()`
- duplicate hyphen/underscore variants are deduplicated in file listings

This matters because module names are underscore-based, while class names are usually CamelCase.

## Host-side phase

### Create
- `create-fsm --name <name>` writes or overwrites source in the artifact FSM directory.
- if no content is supplied, Asteria generates a simple template.

### Compile
- `compile-fsm --name <name>` runs `genfsm` and writes generated Python beside the source file.
- compile is host-side and does not require live robot runtime.

## Live phase

### Preconditions
Before `run-fsm`:
- daemon reachable
- robot connected
- lease held by the intended controller
- `connection.supports_fsm_runtime == true`

### Run
- CLI surface: `run-fsm --module <name>`
- the daemon auto-compiles first if the generated Python is stale or missing
- starting a new FSM replaces the previously loaded one

### Event injection
- `send-text --message <text>`
- `send-speech --message <text>`

These require:
- connected full runtime
- an active running FSM

## Stop paths

- `stop-all`: halt motion, usually unload active FSM
- `stop-all --keep-fsm`: halt motion, preserve loaded FSM
- `unload-fsm`: clear the active FSM explicitly

For normal safety, prefer unload-oriented endings.

## Best starter program

`agent_smoke_test` is the best known no-motion live probe:
- easy to run
- validates runtime, load, and event injection
- safe baseline before experimenting with more ambitious behaviors
