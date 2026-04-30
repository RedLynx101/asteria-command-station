# Asteria Stack Overview

This document is the short answer to "what is actually in Asteria right now?"

## Current Architecture

```text
Desktop Browser
        |
        |  serves GUI + JSON APIs
        v
asteria/daemon/server.py
        |
        |  dispatches actions, owns leases, exposes status
        v
asteria/daemon/runtime.py
        |
        +-- FSM helpers in asteria/tools/fsm.py
        +-- image artifacts in asteria/artifacts/images/
        +-- run reports in asteria/artifacts/runs/
        +-- mobile bridge adapter in asteria/mobile/runtime_adapter.py
```

Handheld clients do not talk to a separate mobile app server. They call `/api/mobile/*` on the same daemon.

## Surfaces

### Desktop operator surface

- source: `asteria/gui-app/` preferred, `asteria/gui/` legacy fallback
- transport: same-origin browser calls to `/api/status`, `/api/command`, lease routes, and artifact URLs
- purpose: primary local operator console

### Mobile / handheld surface

- source: `asteria/mobile/`
- transport: bearer-authenticated `/api/mobile/*` routes served by the daemon
- purpose: thin remote control / status / chat-session bridge for handheld clients

### old-3DS client

- source: `apps/asteria-ds/`
- transport: HTTP GET/POST calls to the mobile bridge
- purpose: experimental handheld control client and future daemon companion app

## Data Ownership

`runtime.py` is the center of the stack. It owns:

- robot connection state
- control lease policy
- prompt and activity logs
- prompt forward mode and worker state
- recent command log
- background Codex job tracking
- FSM files and compile/run flow
- latest image capture metadata
- last command result shown in both desktop and mobile UIs

That means new clients should prefer adapting the runtime instead of creating parallel robot-control state.

## What Was Merged From The External Pack

Imported and adapted:

- redesigned bright tabbed GUI
- mobile auth/session/service scaffolding
- old-3DS app scaffold
- mobile config bootstrap script

Not adopted as-is:

- separate FastAPI server assumption
- unsupported command set (`place`, true pickup workflow beyond the current soft-kick fallback)

## Known Gaps

- Mobile chat sessions persist locally, but they are not yet connected to an autonomous worker loop.
- The handheld app still has some UI/history affordances from the older chat-session model even though Desk prompts plus pilot control are the main supported path.
- The legacy `asteria/gui/` surface still exists, but the React `gui-app` build is now the canonical desktop UI path.
