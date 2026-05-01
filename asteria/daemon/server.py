from __future__ import annotations

import argparse
import json
import mimetypes
import socket
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from asteria.daemon.common import env_bool
from asteria.daemon.runtime import AsteriaRuntime
from asteria.mobile.auth import load_auth_config
from asteria.mobile.bridge import MobileBridgeService
from asteria.mobile.runtime_adapter import AsteriaMobileRuntimeAdapter


RUNTIME = AsteriaRuntime()
_MOBILE_SERVICE: MobileBridgeService | None = None
_MOBILE_SERVICE_MTIME: float | None = None

_GUI_APP_DIST = RUNTIME.paths.asteria_root / "gui-app" / "dist"
_PUBLIC_ARTIFACT_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def resolve_mobile_service() -> tuple[MobileBridgeService | None, str | None]:
    global _MOBILE_SERVICE, _MOBILE_SERVICE_MTIME

    config_root = RUNTIME.paths.asteria_root / "artifacts" / "mobile-config"
    config_path = config_root / "mobile-auth.json"
    if not config_path.exists():
        return None, "mobile bridge not configured; run scripts/asteria_mobile_setup.py first"

    mtime = config_path.stat().st_mtime
    if _MOBILE_SERVICE is not None and _MOBILE_SERVICE_MTIME == mtime:
        return _MOBILE_SERVICE, None

    auth = load_auth_config(config_root)
    _MOBILE_SERVICE = MobileBridgeService(
        AsteriaMobileRuntimeAdapter(
            RUNTIME,
            holder_id=auth.holder_id,
            holder_label=auth.holder_label,
        ),
        auth.device_token,
        RUNTIME.paths.asteria_root / "artifacts",
    )
    _MOBILE_SERVICE_MTIME = mtime
    return _MOBILE_SERVICE, None


class AsteriaHandler(BaseHTTPRequestHandler):
    server_version = "AsteriaCommandStation/0.2"

    def log_message(self, format: str, *args) -> None:
        return

    def _send_bytes(self, body: bytes, content_type: str, status_code: int = 200) -> None:
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout, OSError):
            self.close_connection = True

    def _write_json(self, payload: dict, status_code: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self._send_bytes(body, "application/json", status_code)

    def _write_exception(self, exc: Exception, status_code: int = 500) -> None:
        payload = {"ok": False, "error": str(exc)}
        if env_bool("ASTERIA_DEBUG_TRACEBACKS", False):
            payload["traceback"] = traceback.format_exc()
        self._write_json(payload, status_code)

    def _write_file(self, target: Path) -> None:
        content = target.read_bytes()
        mime, _ = mimetypes.guess_type(target.name)
        self._send_bytes(content, mime or "application/octet-stream", 200)

    def _serve_gui(self, relative_path: str) -> None:
        decoded_path = unquote(relative_path.lstrip("/"))

        # Prefer the React app build output (gui-app/dist) if it exists.
        if _GUI_APP_DIST.is_dir():
            dist_root = _GUI_APP_DIST.resolve()
            candidate = (dist_root / decoded_path).resolve()
            try:
                candidate.relative_to(dist_root)
            except ValueError:
                self._write_json({"ok": False, "error": "not found"}, 404)
                return
            if candidate.exists() and candidate.is_file():
                self._write_file(candidate)
                return
            # SPA fallback: unknown paths serve index.html for client-side routing.
            spa_index = _GUI_APP_DIST / "index.html"
            if spa_index.exists() and "." not in decoded_path.split("/")[-1]:
                self._write_file(spa_index)
                return

        # Fall back to the legacy vanilla GUI.
        gui_root = RUNTIME.paths.gui_root.resolve()
        target = (gui_root / decoded_path).resolve()
        try:
            target.relative_to(gui_root)
        except ValueError:
            self._write_json({"ok": False, "error": "not found"}, 404)
            return
        if not target.exists() or not target.is_file():
            self._write_json({"ok": False, "error": "not found"}, 404)
            return
        self._write_file(target)

    def _serve_artifact(self, relative_path: str) -> None:
        decoded_path = unquote(relative_path.lstrip("/"))
        if decoded_path == "artifacts":
            decoded_path = ""
        elif decoded_path.startswith("artifacts/"):
            decoded_path = decoded_path.removeprefix("artifacts/")

        artifacts_root = RUNTIME.paths.artifacts_root.resolve()
        target = (artifacts_root / decoded_path).resolve()
        try:
            target.relative_to(artifacts_root)
        except ValueError:
            self._write_json({"ok": False, "error": "not found"}, 404)
            return
        if not target.exists() or not target.is_file():
            self._write_json({"ok": False, "error": "not found"}, 404)
            return
        try:
            target.relative_to(RUNTIME.paths.image_root.resolve())
        except ValueError:
            self._write_json({"ok": False, "error": "not found"}, 404)
            return
        if target.suffix.lower() not in _PUBLIC_ARTIFACT_SUFFIXES:
            self._write_json({"ok": False, "error": "not found"}, 404)
            return
        self._write_file(target)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload must be an object")
            return payload
        except Exception as exc:
            self._write_json({"ok": False, "error": f"invalid JSON: {exc}"}, 400)
            return None

    def _authorized_mobile_service(self) -> MobileBridgeService | None:
        service, error = resolve_mobile_service()
        if service is None:
            self._write_json({"ok": False, "error": error}, 503)
            return None

        token = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        try:
            service.check_auth(token)
        except PermissionError as exc:
            self._write_json({"ok": False, "error": str(exc)}, 401)
            return None
        return service

    def _handle_mobile_get(self, parsed) -> bool:
        service = self._authorized_mobile_service()
        if service is None:
            return True

        parts = [part for part in parsed.path.split("/") if part]
        query = parse_qs(parsed.query)
        try:
            if parts == ["api", "mobile", "bootstrap"]:
                self._write_json(service.bootstrap())
                return True
            if parts == ["api", "mobile", "status"]:
                self._write_json(service.status())
                return True
            if parts == ["api", "mobile", "chat", "sessions"]:
                self._write_json({"ok": True, "items": service.list_sessions()})
                return True
            if parts == ["api", "mobile", "images", "latest"]:
                self._write_json(service.latest_image())
                return True
            if parts == ["api", "mobile", "images", "preview"]:
                width = max(80, min(240, int(query.get("width", ["176"])[0])))
                height = max(60, min(180, int(query.get("height", ["132"])[0])))
                self._send_bytes(service.latest_image_preview_rgb565(width=width, height=height), "application/octet-stream", 200)
                return True
            if len(parts) == 5 and parts[:4] == ["api", "mobile", "chat", "sessions"]:
                self._write_json(service.get_session(unquote(parts[4])))
                return True
            self._write_json({"ok": False, "error": "not found"}, 404)
            return True
        except Exception as exc:
            self._write_exception(exc)
            return True

    def _handle_mobile_post(self, parsed, payload: dict) -> bool:
        service = self._authorized_mobile_service()
        if service is None:
            return True

        parts = [part for part in parsed.path.split("/") if part]
        try:
            if parts == ["api", "mobile", "chat", "sessions"]:
                self._write_json(service.create_session(title=str(payload.get("title", "New Chat"))))
                return True
            if len(parts) == 6 and parts[:4] == ["api", "mobile", "chat", "sessions"] and parts[5] == "messages":
                self._write_json(service.add_message(unquote(parts[4]), str(payload.get("content", ""))))
                return True
            if len(parts) == 6 and parts[:4] == ["api", "mobile", "chat", "sessions"] and parts[5] == "cancel":
                self._write_json(service.cancel_session_job(unquote(parts[4])))
                return True
            if parts == ["api", "mobile", "teleop", "claim"]:
                self._write_json(service.claim_teleop(
                    holder_id=str(payload.get("holder_id", "asteria-ds")),
                    holder_label=str(payload.get("holder_label", "Asteria DS")),
                    takeover=bool(payload.get("takeover", False)),
                ))
                return True
            if parts == ["api", "mobile", "teleop", "release"]:
                self._write_json(service.release_teleop(holder_id=str(payload.get("holder_id", "asteria-ds"))))
                return True
            if parts == ["api", "mobile", "teleop", "vector"]:
                self._write_json(service.teleop_vector(payload))
                return True
            if parts == ["api", "mobile", "teleop", "stop"]:
                self._write_json(service.teleop_stop())
                return True
            if parts == ["api", "mobile", "teleop", "command"]:
                self._write_json(service.teleop_command(command=str(payload.get("command", "")), payload=payload))
                return True
            if parts == ["api", "mobile", "images", "capture"]:
                self._write_json(service.capture_image())
                return True
            if parts == ["api", "mobile", "prompt"]:
                self._write_json(service.submit_prompt(
                    text=str(payload.get("text", "")),
                    holder_id=str(payload.get("holder_id", "asteria-ds")),
                    holder_label=str(payload.get("holder_label", "Asteria DS")),
                ))
                return True
            self._write_json({"ok": False, "error": "not found"}, 404)
            return True
        except Exception as exc:
            self._write_exception(exc)
            return True

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._serve_gui("index.html")
            return
        if parsed.path.startswith("/assets/"):
            self._serve_gui(parsed.path.lstrip("/"))
            return
        if parsed.path.startswith("/gui/"):
            self._serve_gui(parsed.path.removeprefix("/gui/"))
            return
        if parsed.path.startswith("/artifacts/"):
            self._serve_artifact(parsed.path.removeprefix("/"))
            return
        if parsed.path.startswith("/api/mobile/"):
            self._handle_mobile_get(parsed)
            return
        if parsed.path == "/health":
            self._write_json({"ok": True, "timestamp": RUNTIME.status()["timestamp"]})
            return
        if parsed.path == "/api/status":
            self._write_json({"ok": True, **RUNTIME.status()})
            return
        if parsed.path == "/api/fsms":
            self._write_json({"ok": True, "items": RUNTIME.status().get("fsm_files", [])})
            return
        if parsed.path == "/api/images":
            query = parse_qs(parsed.query)
            latest_only = query.get("latest", ["0"])[0] == "1"
            latest = RUNTIME.latest_image_summary()
            if latest_only:
                items = [latest] if latest else []
            else:
                images = sorted(RUNTIME.paths.image_root.glob("*.jpg"), key=lambda item: item.stat().st_mtime, reverse=True)
                items = [
                    {
                        "name": path.name,
                        "path": str(path),
                        "url": f"/{path.relative_to(RUNTIME.paths.asteria_root).as_posix()}",
                        "updated_at_epoch": path.stat().st_mtime,
                    }
                    for path in images[:20]
                ]
            self._write_json({"ok": True, "items": items})
            return
        self._write_json({"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        payload = self._read_json_body()
        if payload is None:
            return

        if parsed.path.startswith("/api/mobile/"):
            self._handle_mobile_post(parsed, payload)
            return

        try:
            if parsed.path == "/api/command":
                action = str(payload.get("action", "")).strip()
                if not action:
                    self._write_json({"ok": False, "error": "action is required"}, 400)
                    return
                self._write_json(RUNTIME.dispatch(action, payload))
                return
            if parsed.path == "/api/lease/claim":
                self._write_json(RUNTIME.dispatch("lease_claim", payload))
                return
            if parsed.path == "/api/lease/release":
                self._write_json(RUNTIME.dispatch("lease_release", payload))
                return
            self._write_json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self._write_exception(exc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Asteria command station daemon.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 only on a trusted LAN.")
    parser.add_argument("--port", type=int, default=8766, help="Local bind port.")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), AsteriaHandler)
    server.timeout = 0.5
    print(f"Asteria command station listening on http://{args.host}:{args.port}")
    try:
        while not RUNTIME.shutdown_event.is_set():
            server.handle_request()
    finally:
        RUNTIME.disconnect()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
