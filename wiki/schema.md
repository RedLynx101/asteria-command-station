---
kind: schema
status: active
last_reviewed: 2026-04-14
---

# Wiki Schema

This wiki is an agent-maintained knowledge base for Asteria.

## Page types

- **Hub** pages: entry points such as [[index]], [[overview/stack-map]], or [[fsm/fsm-lifecycle]]
- **Operational** pages: distilled guidance for using the robot safely
- **Source summary** pages: summaries of raw docs/code/notes that feed the wiki
- **Procedure** pages: step-by-step playbooks
- **Open question** pages: gaps, contradictions, or unvalidated assumptions

## Required frontmatter

Use these fields when practical:

- `kind`: `index`, `hub`, `operational`, `procedure`, `source-summary`, `notes`, `open-questions`
- `status`: `validated`, `mixed`, `inferred`, `active`
- `runtime`: one or more of `aim_fsm_headless`, `aim_raw_minimal`, `host-side`, `n/a`
- `last_reviewed`: `YYYY-MM-DD`

Not every page needs every field, but hub and operational pages should usually have them.

## Writing rules

1. Prefer short, dense operational notes over essays.
2. Separate facts into:
   - validated live behavior
   - code-defined surface
   - inference or likely behavior
3. Link aggressively with Obsidian-style links.
4. Keep source summaries distinct from synthesized operational pages.
5. Raw source files under `raw/` are immutable copies.
6. When a question produces a durable answer, add it back to the wiki.
7. Update an existing page before creating a new overlapping page.

## Validation language

- **Validated**: observed in live robot use or directly confirmed by current Asteria behavior notes.
- **Code-defined**: present in current repo code or CLI surface, but not necessarily revalidated live.
- **Inferred**: a reasonable synthesis from surrounding code/docs; keep these clearly labeled.

## Link conventions

- Link major concepts on first mention in a section.
- Prefer path-qualified links when names may collide, for example `[[overview/runtime-modes]]`.
- Link from high-level pages down to procedures and sources.
- Link from procedure pages back to the hub pages they depend on.

## Preferred growth pattern

1. ingest source
2. summarize source under `sources/`
3. update one or more operational pages
4. append a short note to [[log]]
5. if uncertainty remains, add it to [[open-questions]]
