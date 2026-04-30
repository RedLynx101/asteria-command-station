# Quickstart

## Disconnected Review

```powershell
cd asteria-command-station
python -m asteria.daemon.server --host 127.0.0.1
```

Open `http://127.0.0.1:8766/`.

The app starts without a robot. This is enough to review the GUI, wiki, FSM files, CLI surface, and mobile bridge shape.

## Build The React GUI

```powershell
cd asteria\gui-app
npm ci
npm run build
cd ..\..
python -m asteria.daemon.server --host 127.0.0.1
```

When `asteria/gui-app/dist` exists, the daemon serves it. Otherwise it serves the legacy static GUI from `asteria/gui/`.

## Generate Asteria DS Config

```powershell
python .\scripts\asteria_mobile_setup.py
```

This writes local private files under `asteria/artifacts/mobile-config/`. They are ignored by Git.

Then copy the generated Asteria DS import config to:

```text
sdmc:/3ds/asteria-ds/config.json
```

## Live Robot Use

Clone the external runtime dependencies into this repo root, then start the daemon:

```powershell
git clone https://github.com/touretzkyds/vex-aim-tools.git
git clone https://github.com/touretzkyds/AIM_Websocket_Library.git
```

Then start Asteria:

```powershell
powershell -ExecutionPolicy Bypass -File .\asteria\start_asteria.ps1 -BindHost 127.0.0.1
```

Use `-BindHost 0.0.0.0` only when a trusted local network client needs mobile access.

For handheld setup, use the paired public repo: [RedLynx101/asteria-ds](https://github.com/RedLynx101/asteria-ds).
