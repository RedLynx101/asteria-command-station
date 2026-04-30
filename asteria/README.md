# Asteria Package Notes

This package contains the runtime code for the Asteria Command Station.

- `daemon/` owns robot state, leases, command dispatch, the stdlib HTTP server, and the desktop GUI API.
- `gui-app/` is the React/Vite command station source. Build it with `npm run build` when you want the daemon to serve the modern UI from `gui-app/dist`.
- `gui/` is the legacy static GUI fallback served when the React build is absent.
- `mobile/` exposes the authenticated bridge used by handheld clients such as Asteria DS.
- `tools/` contains FSM authoring, compilation, and artifact helpers.
- `artifacts/fsm/` contains curated example FSMs that are safe to keep in the public repo.

Project-level setup, screenshots, and public documentation live one directory up in the repository root.

## Run

From the repository root:

```powershell
python -m asteria.daemon.server --host 127.0.0.1
```

Open `http://127.0.0.1:8766/`.

For the helper script:

```powershell
powershell -ExecutionPolicy Bypass -File .\asteria\start_asteria.ps1 -BindHost 127.0.0.1
```

Use `-BindHost 0.0.0.0` only when a trusted device on the same network, such as Asteria DS, needs to reach the mobile bridge.

## Agent Surface

Useful local checks:

```powershell
python -m asteria.cli status
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent list-prompts --pending-only --limit 5
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent log-note --title "Planning" --message "..."
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent create-fsm --name demo_name
python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent compile-fsm --name demo_name
```

Live robot movement requires the external VEX AIM runtime folders described in `../docs/EXTERNAL_REPOS.md`.
