---
kind: index
status: active
last_reviewed: 2026-04-15
---

# Asteria Wiki

This wiki is the compiled operational layer between raw repo sources and future robot/FSM work.

It is optimized for me as an agent, not for polished human documentation. The goal is to answer quickly:
- what Asteria can do right now
- which runtime mode matters for a task
- whether a task should be a direct command or an FSM
- which existing FSM is the best starting point
- what has been validated versus merely inferred from code

## Start here

- [[overview/stack-map]]
- [[overview/runtime-modes]]
- [[robot/capability-matrix]]
- [[fsm/fsm-lifecycle]]
- [[fsm/example-fsms]]
- [[procedures/live-probe-checklist]]
- [[open-questions]]

## Overview

- [[overview/stack-map]]
- [[overview/runtime-modes]]
- [[overview/control-and-leases]]
- [[overview/command-surface]]
- [[overview/desk-prompt-bridge]]
- [[overview/mobile-and-handheld]]

## Robot operation

- [[robot/capability-matrix]]
- [[robot/safety-and-stop-semantics]]

## FSM work

- [[fsm/fsm-lifecycle]]
- [[fsm/fsm-authoring-patterns]]
- [[fsm/example-fsms]]

## Procedures

- [[procedures/live-probe-checklist]]
- [[procedures/recovery-playbooks]]

## Source layer

- [[sources/source-registry]]
- [[sources/llm-wiki-pattern]]
- [[sources/asteria-readme]]
- [[sources/asteria-agent]]
- [[sources/stack-overview]]
- [[sources/gui-app-surface]]
- [[sources/operator-runbook]]
- [[sources/openclaw-setup]]
- [[sources/openclaw-direct-bridge]]
- [[sources/runtime-prompt-flow]]
- [[sources/cli-surface]]
- [[sources/fsm-tooling]]
- [[sources/mobile-runtime-surface]]
- [[sources/validated-runtime-notes-2026-04-14]]
- [[raw/llm-wiki]]

## Maintenance

- [[schema]]
- [[log]]

## Working rules

- Prefer validated behavior over plausible behavior.
- Keep raw sources immutable.
- File useful answers back into the wiki instead of re-deriving them later.
- Update existing pages before creating new fragments.
- Mark uncertainty explicitly.
