---
kind: source-summary
status: mixed
last_reviewed: 2026-04-14
source_file: asteria/tools/fsm.py
---

# Source Summary: FSM Tooling

## Key points extracted

- `slugify()` normalizes FSM names to underscore slugs.
- `class_name_for()` maps names to CamelCase class names.
- default template generation exists for new FSM files.
- compile uses `genfsm` and writes generated Python beside the source file.
- file listing now deduplicates stale hyphen/underscore variants.

## Wiki pages fed by this source

- [[fsm/fsm-lifecycle]]
- [[fsm/fsm-authoring-patterns]]
- [[open-questions]]
