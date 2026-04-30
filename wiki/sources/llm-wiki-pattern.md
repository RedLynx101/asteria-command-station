---
kind: source-summary
status: active
last_reviewed: 2026-04-14
source_file: raw/llm-wiki.md
---

# Source Summary: LLM Wiki Pattern

Raw source: [[raw/llm-wiki]]

## What it contributes

This note provides the design pattern for the whole wiki:
- raw sources stay immutable
- the wiki is a persistent synthesis layer
- index and log matter
- useful query answers should be filed back into the wiki
- the schema should teach the agent how to maintain the wiki

## What I adopted for Asteria

- agent-first organization over human-polished docs
- a distinct raw-source layer
- an explicit schema page
- a log of ingests and updates
- hub pages plus source summaries rather than pure RAG-style rediscovery

## Asteria-specific adaptation

The note is generic. For Asteria, the wiki should center on:
- runtime-mode decisions
- control ownership and stop semantics
- direct-command versus FSM choice
- reusable FSM patterns across the repo
