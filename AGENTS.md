# Agent Guide

You are working in the public Asteria Command Station repo.

## Operating Model

- Treat `python -m asteria.daemon.server` as the local source of truth for robot state.
- Use the CLI before touching live motion: `python -m asteria.cli status`.
- Prefer Desk notes and prompt resolution for coordination with a human operator.
- Prefer FSMs for multi-step, reusable, branching, or repeated behaviors.
- Use direct commands only for bounded probes, calibration, stop, image capture, and simple one-step actions.

## Safety Rules

- Claim a control lease before lease-gated robot actions.
- Stop intentionally: use `stop-all` for immediate halt, `stop-all --keep-fsm` only when preserving the active FSM is intended, and `unload-fsm` when cancelling the behavior itself.
- Do not increase safety limits casually.
- If the robot connection, host, lease holder, or active FSM is unclear, stop motion and report the uncertainty.

## Repo Boundaries

- Do not vendor OpenClaw, VEX AIM tooling, class labs, local virtual environments, or generated mobile secrets into this repo.
- Keep generated runtime data out of Git unless it is a curated example under `asteria/artifacts/fsm/`.
- Keep public docs rooted in relative links.
- Update `wiki/` when behavior has been validated and the note will help future agents.

## Useful Commands

```powershell
python -m asteria.daemon.server --host 127.0.0.1
python -m asteria.cli status
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent list-prompts --pending-only
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent log-note --title "Planning" --message "..."
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent create-fsm --name demo_name
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent compile-fsm --name demo_name
```

## Verification

Before publishing changes:

```powershell
python -m compileall asteria scripts
cd asteria\gui-app
npm ci
npm run build
```

If devkitPro or live VEX AIM dependencies are missing, document that limitation rather than faking validation.
