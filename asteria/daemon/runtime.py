from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import ipaddress
import inspect
import json
import os
import queue
import subprocess
import tempfile
import re
import signal
import socket
import sys
import threading
import time
import textwrap
import traceback
import uuid
from pathlib import Path
from typing import Any

from asteria.daemon.common import AsteriaPaths, ensure_dirs, ensure_import_paths, env_bool, env_float, resolve_paths
from asteria.daemon.models import ActivityEntry, ControlLease, PromptEntry, TelemetrySnapshot
from asteria.openclaw_bridge import OpenClawBridgeClient
from asteria.tools.fsm import class_name_for, compile_fsm_file, create_fsm_file, ensure_compiled_fsm, list_fsm_files, slugify, write_run_artifact


def utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


SCREEN_CENTER_X = 120
SCREEN_CENTER_Y = 120
SCREEN_TEXT_CHAR_WIDTH = 11
SCREEN_TEXT_LINE_HEIGHT = 26
SCREEN_TEXT_WRAP_CHARS = 16
SCREEN_TEXT_MAX_LINES = 3
DEFAULT_CODEX_MODEL = "gpt-5.4-mini"


def wrap_screen_text(text: str) -> list[str]:
    cleaned = " ".join(str(text).split())
    if not cleaned:
        return [""]

    lines = textwrap.wrap(
        cleaned,
        width=SCREEN_TEXT_WRAP_CHARS,
        break_long_words=True,
        break_on_hyphens=False,
    )
    if len(lines) <= SCREEN_TEXT_MAX_LINES:
        return lines

    visible = lines[:SCREEN_TEXT_MAX_LINES]
    last = visible[-1]
    if len(last) > SCREEN_TEXT_WRAP_CHARS - 3:
        last = last[: SCREEN_TEXT_WRAP_CHARS - 3].rstrip()
    visible[-1] = f"{last}..."
    return visible


def screen_text_x(line: str) -> int:
    estimated_width = max(0, len(line)) * SCREEN_TEXT_CHAR_WIDTH
    return max(12, int(SCREEN_CENTER_X - (estimated_width / 2)))


def call_if_supported(target: Any, method_name: str, *args: Any) -> bool:
    method = getattr(target, method_name, None)
    if not callable(method):
        return False
    try:
        method(*args)
    except TypeError:
        if args:
            method()
        else:
            raise
    return True


def render_screen_text(screen: Any, vex_module: Any, text: str) -> None:
    lines = wrap_screen_text(text)
    start_y = int(SCREEN_CENTER_Y - ((len(lines) - 1) * SCREEN_TEXT_LINE_HEIGHT / 2))

    # The connected runtime currently exposes aim_fsm.aim.Screen, which only guarantees
    # clear_screen() and print_at(). Avoid cross-library Color/Font objects here.
    call_if_supported(screen, "clear_screen")

    print_at = getattr(screen, "print_at", None)
    if callable(print_at):
        for index, line in enumerate(lines):
            print_at(line, x=screen_text_x(line), y=start_y + index * SCREEN_TEXT_LINE_HEIGHT)
        return

    set_cursor = getattr(screen, "set_cursor", None)
    print_text = getattr(screen, "print", None)
    if callable(set_cursor) and callable(print_text):
        start_row = max(1, 5 - ((len(lines) - 1) // 2))
        for index, line in enumerate(lines):
            row = start_row + index
            column = max(1, int(12 - (len(line) / 2)))
            set_cursor(row, column)
            print_text(line)
        return

    raise AttributeError("screen object has no supported text rendering method")


def build_openclaw_forward_text(prompt: PromptEntry) -> str:
    return "\n".join(
        [
            "New Asteria desk prompt.",
            "",
            f"prompt_id: {prompt.id}",
            f"submitted_by: {prompt.submitted_label}",
            f"submitted_at: {prompt.submitted_at}",
            "text:",
            prompt.text,
            "",
            "Instructions:",
            "- Treat this as a live Asteria desk prompt.",
            "- If the answer is clear, do the work.",
            "- Resolve the prompt in Asteria using the exact prompt_id.",
            "- If blocked, report the block clearly.",
        ]
    )


class MinimalVisionAdapter:
    def __init__(self, robot0: Any) -> None:
        self._robot0 = robot0

    def get_camera_image(self) -> bytes:
        return self._robot0.get_camera_image()


class MinimalAsteriaRobot:
    def __init__(self, robot0: Any) -> None:
        self.robot0 = robot0
        self.vision = MinimalVisionAdapter(robot0)
        self.erouter = None
        self.runtime_mode = "aim_raw_minimal"
        self.supports_fsm = False

    def get_camera_image(self) -> bytes:
        return self.vision.get_camera_image()


class DummyAimAudioThread(threading.Thread):
    def __init__(self, host: str) -> None:
        super().__init__()
        self.host = host
        self.running = True
        self.daemon = True

    def start(self) -> None:
        return None


class HeadlessViewerStub:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.crosshairs = False
        self.exited = True

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def clear(self) -> None:
        return None

    def __getattr__(self, _name: str) -> Any:
        return lambda *args, **kwargs: None


class HeadlessParticleFilterStub:
    """Keeps the full AIM runtime stable before an FSM installs a real particle filter."""

    LOCALIZED = "localized"
    LOCALIZING = "localizing"
    LOST = "lost"

    def __init__(self, robot: Any) -> None:
        self.robot = robot
        self.state = self.LOST
        self.sensor_model = type("SensorModelStub", (), {"landmarks": {}})()
        self.particles: list[Any] = []
        self.min_log_weight = 0.0
        self.pose = getattr(robot, "pose", None)
        self.variance = (((0.0, 0.0), (0.0, 0.0)), 0.0)

    def clear_landmarks(self) -> None:
        return None

    def set_pose(self, x: float, y: float, theta: float) -> None:
        pose = getattr(self.robot, "pose", None)
        if pose is not None:
            pose.x = x
            pose.y = y
            pose.theta = theta
        self.pose = pose

    def delocalize(self) -> None:
        self.state = self.LOST

    def move(self) -> None:
        return None

    def look_for_new_landmarks(self) -> None:
        return None

    def update_pose_estimate(self) -> Any:
        self.pose = getattr(self.robot, "pose", None)
        return self.pose

    def update_pose_variance(self) -> Any:
        return self.variance


class AsteriaRuntime:
    def __init__(self) -> None:
        self.paths: AsteriaPaths = resolve_paths()
        ensure_dirs(self.paths)
        ensure_import_paths(self.paths)
        self._lock = threading.RLock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._aim_fsm = None
        self._aim_program = None
        self._evbase = None
        self._pilot = None
        self._state_machine_program_cls = None
        self._text_event_cls = None
        self._speech_event_cls = None
        self._vex = None
        self._aim_transport = None
        self._runtime_error = ""
        self._fsm_modules: dict[str, Any] = {}
        self.robot: Any = None
        self.connected_host: str | None = None
        self.connected_runtime_mode: str | None = None
        self.started_at = time.time()
        self.last_error = ""
        self.command_log: list[dict[str, Any]] = []
        self.activity_log: list[ActivityEntry] = []
        self.prompt_log_path = self.paths.asteria_root / "artifacts" / "desk" / "prompt-log.json"
        self.prompt_log: list[PromptEntry] = self._load_prompt_log()
        self._error_log_path = self.paths.artifacts_root / "error-log.jsonl"
        self._error_log: list[dict[str, Any]] = self._load_error_log()
        self._robot_task_queue: queue.Queue[Any] = queue.Queue()
        self._robot_thread: threading.Thread | None = None
        self.last_result: dict[str, Any] = {}
        self.shutdown_event = threading.Event()
        self.telemetry = TelemetrySnapshot()
        self.lease = self._new_unclaimed_lease()
        self.lease_timeout_sec = env_float("ASTERIA_LEASE_TIMEOUT_SEC", 60.0)
        self.enable_speech = env_bool("OPENCLAW_VEX_AIM_ENABLE_SPEECH", False)
        self.retry_max_sec = env_float("OPENCLAW_VEX_AIM_RETRY_MAX_SEC", 20.0)
        self.safe_max_move_mm = env_float("OPENCLAW_VEX_AIM_SAFE_MAX_MOVE_MM", 800.0)
        self.safe_max_turn_deg = env_float("OPENCLAW_VEX_AIM_SAFE_MAX_TURN_DEG", 360.0)
        self.connection_profiles = self._discover_profiles()
        self.network_map = self._load_network_map()
        self.active_profile = self._initial_profile()
        self._apply_profile_env_defaults(self.active_profile)
        self.profile_connection = self._load_profile_connection(self.active_profile)
        self.connection_override_input = os.getenv("ASTERIA_ROBOT_TARGET_OVERRIDE", "").strip() or None
        if self.connection_override_input is None:
            self.connection_override_input = os.getenv("ASTERIA_ROBOT_HOST_OVERRIDE", "").strip() or None
        self.connection_override_host = self._normalize_robot_target(self.connection_override_input, self.active_profile)
        self.connection_manual_fallbacks = self._split_hosts(os.getenv("ASTERIA_ROBOT_FALLBACKS", ""))
        self.last_connect_attempt_at: str | None = None
        self.last_connect_attempt_hosts: list[str] = []
        self.connection_diagnostics: dict[str, Any] = {"timestamp": None, "items": []}
        self._sync_connection_env()
        self.openclaw_bridge = OpenClawBridgeClient.from_env()
        self.bridge_last_attempt_at: str | None = None
        self.bridge_last_error: str | None = None
        self.bridge_last_status_code: int | None = None
        self.bridge_last_response_id: str | None = None
        self._prompt_forward_inflight: set[str] = set()
        self.prompt_forward_retry_base_sec = max(5.0, env_float("ASTERIA_OPENCLAW_BRIDGE_RETRY_BASE_SEC", 15.0))
        self.prompt_forward_retry_max_sec = max(
            self.prompt_forward_retry_base_sec,
            env_float("ASTERIA_OPENCLAW_BRIDGE_RETRY_MAX_SEC", 300.0),
        )
        self.prompt_forward_stale_sec = max(30.0, env_float("ASTERIA_OPENCLAW_BRIDGE_STALE_SEC", 180.0))
        self._resume_pending_prompt_forwards()

    def _record(self, action: str, payload: dict[str, Any]) -> None:
        event = {"timestamp": utc_ts(), "action": action, "payload": payload}
        self.command_log.append(event)
        if len(self.command_log) > 250:
            self.command_log = self.command_log[-250:]
        if action not in {"submit_prompt", "log_note", "resolve_prompt", "set_codex_timeout", "get_codex_output", "kill_codex_job", "get_error_log"}:
            actor = self._actor_from_payload(payload)
            self._append_activity(
                actor_id=actor["actor_id"],
                actor_label=actor["actor_label"],
                actor_kind=actor["actor_kind"],
                kind="action",
                title=self._action_title(action),
                detail=self._action_detail(action, payload),
                status="info",
                related_action=action,
            )

    def _actor_from_payload(self, payload: dict[str, Any]) -> dict[str, str]:
        actor_id = str(payload.get("holder_id", "system")).strip() or "system"
        actor_label = str(payload.get("holder_label", actor_id)).strip() or actor_id
        actor_kind = str(payload.get("holder_kind", "system")).strip() or "system"
        if actor_id == "openclaw" and actor_kind == "agent":
            actor_label = actor_label or "OpenClaw"
        return {
            "actor_id": actor_id,
            "actor_label": actor_label,
            "actor_kind": actor_kind,
        }

    def _append_activity(
        self,
        *,
        actor_id: str,
        actor_label: str,
        actor_kind: str,
        kind: str,
        title: str,
        detail: str = "",
        status: str = "info",
        related_action: str | None = None,
        prompt_id: str | None = None,
    ) -> None:
        entry = ActivityEntry(
            id=str(uuid.uuid4()),
            timestamp=utc_ts(),
            actor_id=actor_id,
            actor_label=actor_label,
            actor_kind=actor_kind,
            kind=kind,
            title=title,
            detail=detail,
            status=status,
            related_action=related_action,
            prompt_id=prompt_id,
        )
        self.activity_log.append(entry)
        if len(self.activity_log) > 250:
            self.activity_log = self.activity_log[-250:]

    def _action_title(self, action: str) -> str:
        labels = {
            "lease_claim": "Control claim requested",
            "lease_release": "Control release requested",
            "connect": "Robot connect requested",
            "disconnect": "Robot disconnect requested",
            "reconnect": "Robot reconnect requested",
            "set_connection_config": "Connection target updated",
            "save_profile_robot_target": "Profile robot target saved",
            "diagnose_connection": "Connection diagnostics requested",
            "run_fsm": "FSM run requested",
            "unload_fsm": "Active FSM unload requested",
            "create_fsm": "FSM source saved",
            "compile_fsm": "FSM compile requested",
            "send_text": "FSM text event sent",
            "send_speech": "FSM speech event sent",
            "stop_all": "Emergency stop requested",
            "drive_at": "Continuous drive updated",
            "turn_at": "Continuous turn updated",
            "capture_image": "Camera capture requested",
            "move": "Move command issued",
            "sideways": "Sideways move issued",
            "turn": "Turn command issued",
            "say": "Display text issued",
            "kick": "Kick command issued",
        }
        return labels.get(action, action.replace("_", " ").title())

    def _action_detail(self, action: str, payload: dict[str, Any]) -> str:
        if action == "move":
            return f"{payload.get('distance_mm', 0)} mm at {payload.get('angle_deg', 0)} deg"
        if action == "sideways":
            return f"{payload.get('distance_mm', 0)} mm"
        if action == "turn":
            return f"{payload.get('angle_deg', 0)} deg"
        if action == "drive_at":
            return f"{payload.get('angle_deg', 0)} deg @ {payload.get('speed_pct', 0)}%"
        if action == "turn_at":
            return f"{payload.get('turn_rate_pct', 0)}%"
        if action == "say":
            return str(payload.get("text", "")).strip()
        if action == "kick":
            return str(payload.get("style", "medium")).strip()
        if action == "create_fsm":
            return str(payload.get("name", "")).strip()
        if action == "compile_fsm":
            return str(payload.get("name") or payload.get("fsm_path") or "").strip()
        if action == "run_fsm":
            return str(payload.get("module", "")).strip()
        if action == "unload_fsm":
            return str(payload.get("fsm_name") or "active fsm").strip()
        if action in {"send_text", "send_speech"}:
            return str(payload.get("message", "")).strip()
        if action == "stop_all":
            return "stop motion + unload active fsm" if bool(payload.get("stop_fsm", True)) else "stop motion only"
        if action in {"set_connection_config", "save_profile_robot_target"}:
            return str(payload.get("robot_target") or payload.get("override_host") or payload.get("profile") or "").strip()
        return ""

    def _remember_result(self, result: dict[str, Any]) -> dict[str, Any]:
        message = result.get("message")
        ok = bool(result.get("ok", False))
        error = result.get("error")
        if message is None and ok and result.get("generated_exists") is True:
            message = "FSM compiled successfully" if result.get("compiled_now") else "Generated Python is available"
        if message is None and ok and result.get("generated_exists") is False:
            message = "FSM source saved without generated Python"
        self.last_result = {
            "timestamp": utc_ts(),
            "ok": ok,
            "message": message,
            "error": error,
            "fsm_name": result.get("fsm_name"),
            "generated_exists": result.get("generated_exists"),
            "generated_py": result.get("generated_py"),
            "compiled_now": result.get("compiled_now"),
            "artifact_dir": result.get("artifact_dir"),
            "image_path": result.get("image_path"),
            "warning": result.get("warning"),
            "forward_status": result.get("forward_status"),
            "forward_error": result.get("forward_error"),
            "forward_attempts": result.get("forward_attempts"),
            "bridge_session_key": result.get("bridge_session_key"),
        }
        result["last_result"] = self.last_result
        if not ok and error:
            self._log_error(error, result)
        return result

    def _log_error(self, error: str, context: dict[str, Any] | None = None) -> None:
        entry = {
            "timestamp": utc_ts(),
            "error": error,
            "traceback": (context or {}).get("traceback"),
            "action": (context or {}).get("action") or self.command_log[-1]["action"] if self.command_log else None,
            "warning": (context or {}).get("warning"),
            "fsm_name": (context or {}).get("fsm_name"),
        }
        entry = {k: v for k, v in entry.items() if v is not None}
        self._error_log.append(entry)
        if len(self._error_log) > 200:
            self._error_log = self._error_log[-200:]
        try:
            self._error_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._error_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            # Trim file if it gets too large (keep last 200 lines).
            lines = self._error_log_path.read_text(encoding="utf-8").splitlines()
            if len(lines) > 200:
                self._error_log_path.write_text("\n".join(lines[-200:]) + "\n", encoding="utf-8")
        except Exception:
            pass

    def get_error_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        limit = max(1, min(int(payload.get("limit", 20)), 200))
        return {
            "ok": True,
            "errors": self._error_log[-limit:],
            "total": len(self._error_log),
            **self.status(),
        }

    def _set_error(self, message: str) -> None:
        self.last_error = message
        self.telemetry.last_error = message

    def _artifact_url(self, target: Path) -> str | None:
        try:
            relative = target.resolve().relative_to(self.paths.asteria_root.resolve())
        except ValueError:
            return None
        return f"/{relative.as_posix()}"

    def _image_summary(self, target: Path) -> dict[str, Any]:
        updated_at = target.stat().st_mtime
        return {
            "path": str(target),
            "url": self._artifact_url(target),
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(updated_at)),
            "width": None,
            "height": None,
        }

    def latest_image_summary(self) -> dict[str, Any]:
        candidate_path = self.telemetry.last_image_path
        if candidate_path:
            target = Path(candidate_path)
            if target.exists():
                return self._image_summary(target)

        images = sorted(self.paths.image_root.glob("*.jpg"), key=lambda item: item.stat().st_mtime, reverse=True)
        if images:
            return self._image_summary(images[0])
        return {}

    def _split_hosts(self, raw: Any) -> list[str]:
        if raw is None:
            return []
        if isinstance(raw, (list, tuple)):
            values = raw
        else:
            values = str(raw).split(",")
        hosts: list[str] = []
        seen: set[str] = set()
        for value in values:
            host = str(value).strip()
            if not host or host in seen:
                continue
            hosts.append(host)
            seen.add(host)
        return hosts

    def _discover_profiles(self) -> list[str]:
        items: list[str] = []
        config_dir = self.paths.repo_root / "robot-env"
        for env_file in sorted(config_dir.glob(".env.*")):
            match = re.match(r"^\.env\.([A-Za-z0-9_-]+)(?:\.local|\.example)?$", env_file.name)
            if not match:
                continue
            name = match.group(1).lower()
            if name in {"shared", "local"} or name.endswith(".example"):
                continue
            if name not in items:
                items.append(name)
        return items

    def _load_network_map(self) -> dict[str, Any]:
        target = self.paths.repo_root / "robot-env" / "network-map.json"
        if not target.exists():
            return {"defaultProfile": "home", "ssidProfiles": {}}
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return {"defaultProfile": "home", "ssidProfiles": {}}
        if not isinstance(payload, dict):
            return {"defaultProfile": "home", "ssidProfiles": {}}
        ssid_profiles = payload.get("ssidProfiles")
        if not isinstance(ssid_profiles, dict):
            ssid_profiles = {}
        return {
            "defaultProfile": str(payload.get("defaultProfile", "home")).lower(),
            "ssidProfiles": {str(key): str(value).lower() for key, value in ssid_profiles.items()},
        }

    def _initial_profile(self) -> str:
        requested = (
            os.getenv("ASTERIA_ACTIVE_PROFILE", "").strip().lower()
            or os.getenv("COGROB_ACTIVE_PROFILE", "").strip().lower()
        )
        if requested and requested in self.connection_profiles:
            return requested
        default_profile = str(self.network_map.get("defaultProfile", "home")).lower()
        if default_profile in self.connection_profiles:
            return default_profile
        if self.connection_profiles:
            return self.connection_profiles[0]
        return default_profile or "home"

    def _parse_env_file(self, target: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        if not target.exists():
            return values
        for raw_line in target.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            name, raw_value = line.split("=", 1)
            name = name.strip()
            value = raw_value.strip()
            if not name:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            value = value.replace("${REPO_ROOT}", str(self.paths.repo_root))
            value = os.path.expandvars(value)
            values[name] = value
        return values

    def _normalize_robot_target(self, raw: str | None, profile: str | None = None) -> str | None:
        value = str(raw or "").strip()
        if not value:
            return None

        normalized = value
        try:
            ipaddress.ip_address(normalized)
            return normalized
        except ValueError:
            pass

        hex_only = re.fullmatch(r"[0-9A-Fa-f]{8}", normalized)
        if hex_only:
            normalized = f"AIM-{normalized.upper()}"

        if "." not in normalized and normalized.upper().startswith("AIM-"):
            active_profile = (profile or self.active_profile or "").lower()
            if active_profile == "cmu":
                return f"{normalized}.wifi.local.cmu.edu"
            return normalized

        return normalized

    def _robot_id_for_target(self, target: str | None) -> str | None:
        value = str(target or "").strip()
        if not value:
            return None
        match = re.match(r"^(AIM-[A-Za-z0-9]+)", value, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    def _load_profile_connection(self, profile: str) -> dict[str, Any]:
        config_dir = self.paths.repo_root / "robot-env"
        targets = [
            config_dir / ".env.shared",
            config_dir / f".env.{profile}",
            config_dir / ".env.local",
            config_dir / f".env.{profile}.local",
        ]
        merged: dict[str, str] = {}
        loaded_files: list[str] = []
        for target in targets:
            if not target.exists():
                continue
            merged.update(self._parse_env_file(target))
            loaded_files.append(target.name)
        raw_robot_target = str(merged.get("ROBOT", "")).strip() or None
        resolved_robot_host = self._normalize_robot_target(raw_robot_target, profile)
        return {
            "profile": profile,
            "loaded_files": loaded_files,
            "robot_target_input": raw_robot_target,
            "robot_host": resolved_robot_host,
            "robot_id": self._robot_id_for_target(resolved_robot_host or raw_robot_target),
            "fallback_hosts": self._split_hosts(merged.get("OPENCLAW_VEX_AIM_HOST_FALLBACKS", "")),
        }

    def _apply_profile_env_defaults(self, profile: str) -> None:
        config_dir = self.paths.repo_root / "robot-env"
        targets = [
            config_dir / ".env.shared",
            config_dir / f".env.{profile}",
            config_dir / ".env.local",
            config_dir / f".env.{profile}.local",
        ]
        for target in targets:
            if not target.exists():
                continue
            for name, value in self._parse_env_file(target).items():
                if name not in os.environ:
                    os.environ[name] = value

        fallback_creds = self.paths.repo_root / "asteria-google-cloud.json"
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ and fallback_creds.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(fallback_creds)

    def _effective_fallback_hosts(self) -> list[str]:
        if self.connection_manual_fallbacks:
            return list(self.connection_manual_fallbacks)
        profile_fallbacks = self.profile_connection.get("fallback_hosts") or []
        if profile_fallbacks:
            return list(profile_fallbacks)
        return self._split_hosts(os.getenv("OPENCLAW_VEX_AIM_HOST_FALLBACKS", ""))

    def _effective_primary_host(self) -> str | None:
        if self.connection_override_host:
            return self.connection_override_host
        profile_host = self.profile_connection.get("robot_host")
        if profile_host:
            return str(profile_host)
        env_host = os.getenv("ROBOT", "").strip()
        return env_host or None

    def _candidate_hosts(self, explicit_host: str | None = None) -> list[str]:
        hosts: list[str] = []
        seen: set[str] = set()

        def add(values: Any) -> None:
            for host in self._split_hosts(values):
                if host in seen:
                    continue
                hosts.append(host)
                seen.add(host)

        explicit_primary = self._split_hosts(explicit_host)
        override_primary = self._split_hosts(self.connection_override_host)
        manual_fallbacks = list(self.connection_manual_fallbacks)

        if explicit_primary:
            add(explicit_primary)
            add(manual_fallbacks)
            return hosts

        if override_primary:
            add(override_primary)
            add(manual_fallbacks)
            return hosts

        add(self.profile_connection.get("robot_host"))
        add(os.getenv("ROBOT", ""))
        add(self._effective_fallback_hosts())
        add("192.168.4.1")
        return hosts

    def _sync_connection_env(self) -> None:
        os.environ["ASTERIA_ACTIVE_PROFILE"] = self.active_profile
        if self.connection_override_input:
            os.environ["ASTERIA_ROBOT_TARGET_OVERRIDE"] = self.connection_override_input
        else:
            os.environ.pop("ASTERIA_ROBOT_TARGET_OVERRIDE", None)
        if self.connection_override_host:
            os.environ["ASTERIA_ROBOT_HOST_OVERRIDE"] = self.connection_override_host
        else:
            os.environ.pop("ASTERIA_ROBOT_HOST_OVERRIDE", None)

        if self.connection_manual_fallbacks:
            os.environ["ASTERIA_ROBOT_FALLBACKS"] = ",".join(self.connection_manual_fallbacks)
        else:
            os.environ.pop("ASTERIA_ROBOT_FALLBACKS", None)

        effective_host = self._effective_primary_host()
        if effective_host:
            os.environ["ROBOT"] = effective_host
        elif os.getenv("ROBOT"):
            os.environ.pop("ROBOT", None)

        effective_fallbacks = self._effective_fallback_hosts()
        if effective_fallbacks:
            os.environ["OPENCLAW_VEX_AIM_HOST_FALLBACKS"] = ",".join(effective_fallbacks)
        elif os.getenv("OPENCLAW_VEX_AIM_HOST_FALLBACKS"):
            os.environ.pop("OPENCLAW_VEX_AIM_HOST_FALLBACKS", None)

    def _connection_state(self) -> dict[str, Any]:
        effective_host = self._effective_primary_host()
        source = "profile" if self.profile_connection.get("robot_host") else "environment"
        if self.connection_override_host:
            source = "override"
        elif not effective_host:
            source = "fallback"
        return {
            "profiles": self.connection_profiles,
            "active_profile": self.active_profile,
            "profile_loaded_files": self.profile_connection.get("loaded_files", []),
            "profile_robot_target_input": self.profile_connection.get("robot_target_input"),
            "profile_robot_host": self.profile_connection.get("robot_host"),
            "profile_robot_id": self.profile_connection.get("robot_id"),
            "override_target_input": self.connection_override_input,
            "override_host": self.connection_override_host,
            "resolved_host": effective_host,
            "resolved_robot_id": self._robot_id_for_target(effective_host),
            "connected_runtime_mode": self.connected_runtime_mode,
            "supports_fsm_runtime": bool(getattr(self.robot, "supports_fsm", False)) if self.robot is not None else False,
            "fallback_hosts": self._effective_fallback_hosts(),
            "candidate_hosts": self._candidate_hosts(),
            "target_source": source,
            "default_profile": self.network_map.get("defaultProfile", "home"),
            "ssid_profiles": self.network_map.get("ssidProfiles", {}),
            "last_attempt_at": self.last_connect_attempt_at,
            "last_attempt_hosts": self.last_connect_attempt_hosts,
            "diagnostics": self.connection_diagnostics,
        }

    def configure_connection(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = str(payload.get("profile", "")).strip().lower()
        override_target = payload.get("robot_target", payload.get("override_host"))
        fallback_hosts = payload.get("fallback_hosts")
        clear_override = bool(payload.get("clear_override", False))
        reset_fallbacks = bool(payload.get("reset_fallbacks", False))

        if profile:
            if profile not in self.connection_profiles:
                return {"ok": False, "error": f"unknown profile: {profile}", **self.status()}
            self.active_profile = profile
            self.profile_connection = self._load_profile_connection(profile)

        if clear_override:
            self.connection_override_input = None
            self.connection_override_host = None
        elif override_target is not None:
            self.connection_override_input = str(override_target).strip() or None
            self.connection_override_host = self._normalize_robot_target(self.connection_override_input, self.active_profile)

        if reset_fallbacks:
            self.connection_manual_fallbacks = []
        elif fallback_hosts is not None:
            self.connection_manual_fallbacks = self._split_hosts(fallback_hosts)

        self.connection_diagnostics = {"timestamp": None, "items": []}
        self._sync_connection_env()

    def _prompt_entry_from_dict(self, payload: dict[str, Any]) -> PromptEntry | None:
        def _clean_optional(value: Any) -> str | None:
            text = str(value or "").strip()
            if not text or text.lower() == "none":
                return None
            return text

        prompt_id = str(payload.get("id", "")).strip()
        submitted_at = str(payload.get("submitted_at", "")).strip()
        submitted_by = str(payload.get("submitted_by", "")).strip()
        submitted_label = str(payload.get("submitted_label", "")).strip()
        text = str(payload.get("text", "")).strip()
        if not prompt_id or not submitted_at or not submitted_label or not text:
            return None
        try:
            forward_attempts = max(0, int(payload.get("forward_attempts", 0) or 0))
        except (TypeError, ValueError):
            forward_attempts = 0
        return PromptEntry(
            id=prompt_id,
            submitted_at=submitted_at,
            submitted_by=submitted_by,
            submitted_label=submitted_label,
            text=text,
            status=str(payload.get("status", "pending") or "pending"),
            forward_status=str(payload.get("forward_status", "not_sent") or "not_sent"),
            forwarded_at=_clean_optional(payload.get("forwarded_at")),
            forward_error=_clean_optional(payload.get("forward_error")),
            forward_attempts=forward_attempts,
            bridge_session_key=_clean_optional(payload.get("bridge_session_key")),
            response=_clean_optional(payload.get("response")),
            resolved_at=_clean_optional(payload.get("resolved_at")),
            resolved_by=_clean_optional(payload.get("resolved_by")),
            resolved_label=_clean_optional(payload.get("resolved_label")),
        )

    def _load_error_log(self) -> list[dict[str, Any]]:
        if not self._error_log_path.exists():
            return []
        try:
            lines = self._error_log_path.read_text(encoding="utf-8").splitlines()
            entries = []
            for line in lines[-200:]:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
            return entries
        except Exception:
            return []

    def _load_prompt_log(self) -> list[PromptEntry]:
        path = self.prompt_log_path
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

        items = payload if isinstance(payload, list) else payload.get("items", [])
        prompts: list[PromptEntry] = []
        if not isinstance(items, list):
            return prompts
        for item in items:
            if not isinstance(item, dict):
                continue
            prompt = self._prompt_entry_from_dict(item)
            if prompt is not None:
                prompts.append(prompt)
        return prompts[-100:]

    def _save_prompt_log_locked(self) -> None:
        self.prompt_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_log_path.write_text(
            json.dumps([entry.as_dict() for entry in self.prompt_log[-100:]], indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _append_memory_note_locked(self, message: str) -> None:
        if not message:
            return
        memory_dir = self.paths.repo_root / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_path = memory_dir / f"{time.strftime('%Y-%m-%d')}.md"
        with memory_path.open("a", encoding="utf-8") as handle:
            handle.write(f"- {message}\n")

    def _pending_prompts_locked(self) -> list[PromptEntry]:
        return [entry for entry in self.prompt_log if entry.status != "resolved"]
        target = self._effective_primary_host() or "fallback sequence"
        return {"ok": True, "message": f"connection target set to {target}", **self.status()}

    def _next_prompt_retry_delay_sec(self, prompt: PromptEntry) -> float:
        exponent = max(0, prompt.forward_attempts - 1)
        delay = self.prompt_forward_retry_base_sec * (2**min(exponent, 5))
        return min(delay, self.prompt_forward_retry_max_sec)

    def _is_stale_sent_prompt(self, prompt: PromptEntry) -> bool:
        if prompt.status == "resolved" or prompt.forward_status != "sent" or not prompt.forwarded_at:
            return False
        try:
            forwarded_at = dt.datetime.strptime(prompt.forwarded_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return True
        age_sec = max(0.0, (dt.datetime.now(dt.timezone.utc) - forwarded_at).total_seconds())
        return age_sec >= self.prompt_forward_stale_sec

    def _queue_prompt_forward(self, prompt_id: str, *, retry: bool = False, delay_sec: float = 0.0) -> dict[str, Any]:
        resolved_session_key = self.openclaw_bridge.session_key_for_prompt(prompt_id)
        with self._lock:
            prompt = self._find_prompt_locked(prompt_id)
            if prompt is None:
                return {"ok": False, "error": f"prompt not found: {prompt_id}", **self.status()}
            if prompt.status == "resolved":
                return {"ok": False, "error": "prompt already resolved", "prompt": prompt.as_dict(), **self.status()}
            if prompt.forward_status == "sent" and not (retry or self._is_stale_sent_prompt(prompt)):
                return {"ok": True, "message": "prompt already forwarded", "prompt": prompt.as_dict(), **self.status()}
            if not self.openclaw_bridge.config.enabled:
                prompt.forward_status = "not_sent"
                prompt.forward_error = "direct bridge disabled"
                prompt.bridge_session_key = resolved_session_key
                self._save_prompt_log_locked()
                return {
                    "ok": True,
                    "message": "prompt submitted; direct OpenClaw bridge is disabled",
                    "warning": "direct bridge disabled",
                    "prompt": prompt.as_dict(),
                    **self._prompt_forward_meta(prompt),
                    **self.status(),
                }
            prompt.bridge_session_key = resolved_session_key
            prompt.forward_status = "retrying" if (retry or prompt.forward_attempts > 0) else "queued"
            prompt.forward_error = None
            self._save_prompt_log_locked()
            prompt_dict = prompt.as_dict()
            if prompt_id in self._prompt_forward_inflight:
                return {
                    "ok": True,
                    "message": "prompt forward already queued",
                    "prompt": prompt_dict,
                    **self._prompt_forward_meta(PromptEntry(**prompt_dict)),
                    **self.status(),
                }
            self._prompt_forward_inflight.add(prompt_id)

        thread = threading.Thread(
            target=self._run_prompt_forward_job,
            args=(prompt_id, retry, delay_sec),
            name=f"asteria-prompt-forward-{prompt_id}",
            daemon=True,
        )
        thread.start()
        return {
            "ok": True,
            "message": "prompt submitted and queued for OpenClaw forward",
            "prompt": prompt_dict,
            **self._prompt_forward_meta(PromptEntry(**prompt_dict)),
            **self.status(),
        }

    def _run_prompt_forward_job(self, prompt_id: str, retry: bool, delay_sec: float) -> None:
        if delay_sec > 0 and self.shutdown_event.wait(delay_sec):
            with self._lock:
                self._prompt_forward_inflight.discard(prompt_id)
            return

        result = self._forward_prompt_entry(prompt_id, retry=retry)

        should_retry = False
        retry_delay = 0.0
        with self._lock:
            self._prompt_forward_inflight.discard(prompt_id)
            prompt = self._find_prompt_locked(prompt_id)
            if (
                prompt is not None
                and prompt.status != "resolved"
                and prompt.forward_status != "sent"
                and self.openclaw_bridge.config.enabled
                and result.get("warning")
            ):
                should_retry = True
                retry_delay = self._next_prompt_retry_delay_sec(prompt)

        if should_retry:
            self._queue_prompt_forward(prompt_id, retry=True, delay_sec=retry_delay)

    def _resume_pending_prompt_forwards(self) -> None:
        if not self.openclaw_bridge.config.enabled:
            return
        pending_ids = [
            entry.id
            for entry in self.prompt_log
            if entry.status != "resolved" and (entry.forward_status != "sent" or self._is_stale_sent_prompt(entry))
        ]
        for prompt_id in pending_ids:
            self._queue_prompt_forward(prompt_id, retry=True)

    def _bridge_state(self) -> dict[str, Any]:
        config = self.openclaw_bridge.config
        return {
            "enabled": config.enabled,
            "gateway_url": config.gateway_url,
            "gateway_path": config.gateway_path,
            "health_url": config.health_url,
            "endpoint_url": config.endpoint_url,
            "session_key": config.session_key,
            "session_key_template": config.session_key_template,
            "timeout_ms": config.timeout_ms,
            "model": config.model,
            "user": config.user,
            "auto_start": config.auto_start,
            "auto_start_timeout_ms": config.auto_start_timeout_ms,
            "last_attempt_at": self.bridge_last_attempt_at,
            "last_error": self.bridge_last_error,
            "last_status_code": self.bridge_last_status_code,
            "last_response_id": self.bridge_last_response_id,
        }

    def _find_prompt_locked(self, prompt_id: str) -> PromptEntry | None:
        for prompt in self.prompt_log:
            if prompt.id == prompt_id:
                return prompt
        return None

    def _prompt_forward_meta(self, prompt: PromptEntry) -> dict[str, Any]:
        return {
            "forward_status": prompt.forward_status,
            "forward_error": prompt.forward_error,
            "forward_attempts": prompt.forward_attempts,
            "bridge_session_key": prompt.bridge_session_key,
        }

    def _forward_prompt_entry(self, prompt_id: str, *, retry: bool = False) -> dict[str, Any]:
        actor = {
            "actor_id": "asteria-bridge",
            "actor_label": "Asteria Bridge",
            "actor_kind": "system",
        }
        resolved_session_key = self.openclaw_bridge.session_key_for_prompt(prompt_id)
        with self._lock:
            prompt = self._find_prompt_locked(prompt_id)
            if prompt is None:
                return {"ok": False, "error": f"prompt not found: {prompt_id}", **self.status()}
            if prompt.status == "resolved":
                return {"ok": False, "error": "prompt already resolved", "prompt": prompt.as_dict(), **self.status()}
            if not retry and prompt.forward_status == "sent":
                return {"ok": True, "message": "prompt already forwarded", "prompt": prompt.as_dict(), **self.status()}
            prompt.bridge_session_key = resolved_session_key
            if retry and self.openclaw_bridge.config.enabled:
                prompt.forward_status = "retrying"
                self._save_prompt_log_locked()
            prompt_snapshot = prompt.as_dict()

        acceptance_state = {"counted": False, "activity_logged": False}

        def handle_accept(response_id: str | None) -> None:
            with self._lock:
                prompt = self._find_prompt_locked(prompt_id)
                if prompt is None:
                    return

                if not acceptance_state["counted"]:
                    prompt.forward_attempts += 1
                    self.bridge_last_attempt_at = utc_ts()
                    acceptance_state["counted"] = True

                prompt.bridge_session_key = resolved_session_key
                prompt.forward_status = "sent"
                prompt.forwarded_at = prompt.forwarded_at or utc_ts()
                prompt.forward_error = None
                self.bridge_last_status_code = 200
                if response_id:
                    self.bridge_last_response_id = response_id
                self.bridge_last_error = None

                if not acceptance_state["activity_logged"]:
                    detail = f"{prompt.id} -> {prompt.bridge_session_key or 'session'}"
                    self._append_activity(
                        actor_id=actor["actor_id"],
                        actor_label=actor["actor_label"],
                        actor_kind=actor["actor_kind"],
                        kind="prompt",
                        title="Prompt forwarded to OpenClaw",
                        detail=detail,
                        status="ok",
                        related_action="submit_prompt",
                        prompt_id=prompt.id,
                    )
                    acceptance_state["activity_logged"] = True

                self._save_prompt_log_locked()

        result = self.openclaw_bridge.forward_prompt(
            build_openclaw_forward_text(PromptEntry(**prompt_snapshot)),
            prompt_id=prompt_id,
            metadata={
                "submitted_by": prompt_snapshot.get("submitted_by"),
                "submitted_label": prompt_snapshot.get("submitted_label"),
                "submitted_at": prompt_snapshot.get("submitted_at"),
                "bridge_session_key": resolved_session_key,
            },
            on_accept=handle_accept,
            session_key=resolved_session_key,
        )

        with self._lock:
            prompt = self._find_prompt_locked(prompt_id)
            if prompt is None:
                return {"ok": False, "error": f"prompt not found after forward: {prompt_id}", **self.status()}

            if result.attempted and not acceptance_state["counted"]:
                prompt.forward_attempts += 1
                self.bridge_last_attempt_at = utc_ts()
            prompt.bridge_session_key = resolved_session_key
            if result.status_code is not None:
                self.bridge_last_status_code = result.status_code
            if result.response_id:
                self.bridge_last_response_id = result.response_id
            self.bridge_last_error = result.error

            if result.accepted:
                prompt.forward_status = "sent"
                prompt.forwarded_at = prompt.forwarded_at or utc_ts()
                if not result.ok and result.error:
                    self._append_activity(
                        actor_id=actor["actor_id"],
                        actor_label=actor["actor_label"],
                        actor_kind=actor["actor_kind"],
                        kind="prompt",
                        title="OpenClaw run reported an error",
                        detail=result.error,
                        status="warn",
                        related_action="submit_prompt",
                        prompt_id=prompt.id,
                    )
                prompt.forward_error = None
            else:
                if result.attempted:
                    prompt.forward_status = "failed"
                else:
                    prompt.forward_status = "not_sent"
                prompt.forward_error = result.error
                detail = result.error or "direct bridge disabled"
                self._append_activity(
                    actor_id=actor["actor_id"],
                    actor_label=actor["actor_label"],
                    actor_kind=actor["actor_kind"],
                    kind="prompt",
                    title="Prompt forward failed" if result.attempted else "Prompt stored locally",
                    detail=detail,
                    status="warn" if result.attempted else "info",
                    related_action="submit_prompt",
                    prompt_id=prompt.id,
                )
            self._save_prompt_log_locked()
            prompt_dict = prompt.as_dict()

        if prompt_dict.get("forward_status") == "sent":
            return {
                "ok": True,
                "message": "prompt forwarded to OpenClaw",
                "prompt": prompt_dict,
                "response_id": result.response_id,
                **self._prompt_forward_meta(PromptEntry(**prompt_dict)),
                **self.status(),
            }

        warning_text = prompt_dict.get("forward_error") or result.error or "direct bridge disabled"
        return {
            "ok": True,
            "message": "prompt submitted locally; OpenClaw forward failed" if result.attempted else "prompt submitted; direct OpenClaw bridge is disabled",
            "warning": warning_text,
            "prompt": prompt_dict,
            **self._prompt_forward_meta(PromptEntry(**prompt_dict)),
            **self.status(),
        }

    def save_profile_robot_target(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = str(payload.get("profile", "")).strip().lower() or self.active_profile
        if profile not in self.connection_profiles:
            return {"ok": False, "error": f"unknown profile: {profile}", **self.status()}

        robot_target = str(payload.get("robot_target", "")).strip()
        if not robot_target:
            return {"ok": False, "error": "robot_target is required", **self.status()}

        normalized_target = self._normalize_robot_target(robot_target, profile)
        env_path = self.paths.repo_root / "robot-env" / f".env.{profile}"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        updated = False
        output_lines: list[str] = []
        for line in existing_lines:
            if re.match(r"^\s*ROBOT\s*=", line):
                output_lines.append(f"ROBOT={normalized_target}")
                updated = True
            else:
                output_lines.append(line)
        if not updated:
            output_lines.append(f"ROBOT={normalized_target}")
        env_path.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")

        if profile == self.active_profile:
            self.profile_connection = self._load_profile_connection(profile)
            if not self.connection_override_input:
                self.connection_override_host = None
            self._sync_connection_env()

        return {"ok": True, "message": f"saved profile robot target for {profile}", **self.status()}

    def diagnose_connection(self, payload: dict[str, Any]) -> dict[str, Any]:
        explicit_host = str(payload.get("host", "")).strip() or None
        items: list[dict[str, Any]] = []
        for host in self._candidate_hosts(explicit_host):
            entry: dict[str, Any] = {"host": host, "resolved_addresses": [], "ip_literal": False}
            try:
                ipaddress.ip_address(host)
                entry["ip_literal"] = True
                entry["resolved_addresses"] = [host]
            except ValueError:
                try:
                    info = socket.getaddrinfo(host, None)
                    entry["resolved_addresses"] = sorted({result[4][0] for result in info})
                except OSError as exc:
                    entry["resolution_error"] = str(exc)
            items.append(entry)
        self.connection_diagnostics = {"timestamp": utc_ts(), "items": items}
        return {"ok": True, "message": "connection diagnostics refreshed", **self.status()}

    def submit_prompt(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", "")).strip()
        if not text:
            return {"ok": False, "error": "text is required", **self.status()}
        forward_mode = str(payload.get("forward_mode", "queue")).strip().lower()
        if forward_mode not in ("queue", "openclaw", "codex"):
            forward_mode = "queue"
        actor = self._actor_from_payload(payload)
        with self._lock:
            prompt_id = f"prompt-{uuid.uuid4().hex[:8]}"
            prompt = PromptEntry(
                id=prompt_id,
                submitted_at=utc_ts(),
                submitted_by=actor["actor_id"],
                submitted_label=actor["actor_label"],
                text=text,
                forward_mode=forward_mode,
                bridge_session_key=self.openclaw_bridge.session_key_for_prompt(prompt_id),
            )
            self.prompt_log.append(prompt)
            if len(self.prompt_log) > 100:
                self.prompt_log = self.prompt_log[-100:]
            self._save_prompt_log_locked()
            self._append_memory_note_locked(
                f"Asteria desk prompt pending from {actor['actor_label']}: {text} [{prompt.id}]"
            )
            self._append_activity(
                actor_id=actor["actor_id"],
                actor_label=actor["actor_label"],
                actor_kind=actor["actor_kind"],
                kind="prompt",
                title=f"Prompt submitted ({forward_mode})",
                detail=text,
                status="pending",
                related_action="submit_prompt",
                prompt_id=prompt.id,
            )

        if forward_mode == "queue":
            with self._lock:
                prompt.forward_status = "not_sent"
                prompt.forward_error = None
                self._save_prompt_log_locked()
            return {
                "ok": True,
                "message": "Prompt queued for manual pickup",
                "prompt": prompt.as_dict(),
                "forward_status": "not_sent",
                **self.status(),
            }

        if forward_mode == "codex":
            with self._lock:
                prompt.forward_status = "queued"
                self._save_prompt_log_locked()
            thread = threading.Thread(
                target=self._run_codex_job,
                args=(prompt.id,),
                daemon=True,
                name=f"codex-{prompt.id}",
            )
            thread.start()
            return {
                "ok": True,
                "message": "Prompt dispatched to Codex agent",
                "prompt": prompt.as_dict(),
                "forward_status": "queued",
                **self.status(),
            }

        queue_result = self._queue_prompt_forward(prompt.id)
        prompt_payload = queue_result.get("prompt", prompt.as_dict())
        response = {
            "ok": True,
            "message": queue_result.get("message"),
            "prompt": prompt_payload,
            "forward_status": prompt_payload.get("forward_status"),
            "forward_error": prompt_payload.get("forward_error"),
            "forward_attempts": prompt_payload.get("forward_attempts"),
            "bridge_session_key": prompt_payload.get("bridge_session_key"),
            **self.status(),
        }
        if queue_result.get("warning"):
            response["warning"] = queue_result.get("warning")
        return response

    # -- Codex agent runner ------------------------------------------------

    _CODEX_PREAMBLE = textwrap.dedent("""\
        You are an Asteria agent -- a host-side robot operator for VEX AIM robots.

        Read asteria/ASTERIA_AGENT.md for your full operating rules.
        Consult and maintain the wiki at asteria/asteria_wiki/ (see index.md).
        Use the Asteria CLI to interact with the daemon at http://127.0.0.1:8766/.

        Key CLI patterns:
          python -m asteria.cli status
          python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent claim-lease --force
          python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent <action>
          python -m asteria.cli --holder-id codex --holder-label Codex --holder-kind agent resolve-prompt --prompt-id {prompt_id} --response "your summary here"

        If something fails (FSM compile error, connection issue, etc.), check the error log:
          curl http://127.0.0.1:8766/api/command -X POST -H "Content-Type: application/json" -d '{{"action":"get_error_log","limit":10}}'
        Or read the persistent error log file at asteria/artifacts/error-log.jsonl.

        When you finish your work, resolve the prompt using the CLI command above.
        If you learn something new about the robot or system, update the wiki.
        Then stop -- do not loop or wait for further input.

        --- PROMPT ---
    """)

    _codex_timeout_minutes: int = 20
    _codex_jobs: dict[str, dict] = {}
    _codex_jobs_lock = threading.Lock()

    def _codex_model(self) -> str:
        return os.getenv("ASTERIA_CODEX_MODEL", "").strip() or DEFAULT_CODEX_MODEL

    def _codex_jobs_summary(self) -> list[dict]:
        with self._codex_jobs_lock:
            out = []
            for pid, info in self._codex_jobs.items():
                out.append({
                    "prompt_id": info.get("prompt_id"),
                    "pid": pid,
                    "model": info.get("model"),
                    "started_at": info.get("started_at"),
                    "output_tail": info.get("output_tail", [])[-30:],
                    "alive": info.get("proc") is not None and info["proc"].poll() is None,
                })
            return out

    def set_codex_timeout(self, payload: dict[str, Any]) -> dict[str, Any]:
        minutes = payload.get("minutes")
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            return {"ok": False, "error": "minutes must be an integer", **self.status()}
        if minutes < 1 or minutes > 60:
            return {"ok": False, "error": "minutes must be 1-60", **self.status()}
        self._codex_timeout_minutes = minutes
        return {"ok": True, "message": f"Codex timeout set to {minutes} minutes", **self.status()}

    def kill_codex_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_id = str(payload.get("prompt_id", "")).strip()
        if not prompt_id:
            return {"ok": False, "error": "prompt_id is required", **self.status()}
        with self._codex_jobs_lock:
            job = None
            for _pid, info in self._codex_jobs.items():
                if info.get("prompt_id") == prompt_id:
                    job = info
                    break
        if job is None:
            return {"ok": False, "error": f"no active codex job for {prompt_id}", **self.status()}
        proc = job.get("proc")
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
        with self._lock:
            prompt = self._find_prompt_locked(prompt_id)
            if prompt and prompt.status != "resolved":
                prompt.forward_status = "failed"
                prompt.forward_error = "killed by operator"
                self._save_prompt_log_locked()
        actor = self._actor_from_payload(payload)
        self._append_activity(
            actor_id=actor["actor_id"],
            actor_label=actor["actor_label"],
            actor_kind=actor["actor_kind"],
            kind="prompt",
            title="Codex agent killed",
            detail=f"Operator killed codex job for {prompt_id}",
            status="warning",
            related_action="kill_codex_job",
            prompt_id=prompt_id,
        )
        return {"ok": True, "message": f"Codex job for {prompt_id} killed", **self.status()}

    def get_codex_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_id = str(payload.get("prompt_id", "")).strip()
        lines = int(payload.get("lines", 30))
        with self._codex_jobs_lock:
            for _pid, info in self._codex_jobs.items():
                if info.get("prompt_id") == prompt_id:
                    tail = info.get("output_tail", [])[-lines:]
                    alive = info.get("proc") is not None and info["proc"].poll() is None
                    return {"ok": True, "output": tail, "alive": alive, **self.status()}
        return {"ok": False, "error": f"no codex job found for {prompt_id}", "output": [], **self.status()}

    def _run_codex_job(self, prompt_id: str) -> None:
        codex_model = self._codex_model()
        codex_path = Path(os.environ.get(
            "CODEX_PATH",
            os.path.expandvars(r"%APPDATA%\npm\codex.cmd"),
        ))
        if not codex_path.exists():
            with self._lock:
                prompt = self._find_prompt_locked(prompt_id)
                if prompt:
                    prompt.forward_status = "failed"
                    prompt.forward_error = f"codex not found at {codex_path}"
                    self._save_prompt_log_locked()
            return

        with self._lock:
            prompt = self._find_prompt_locked(prompt_id)
            if prompt is None or prompt.status == "resolved":
                return
            prompt_text = prompt.text
            prompt.forward_status = "sent"
            prompt.forwarded_at = utc_ts()
            prompt.forward_attempts += 1
            self._save_prompt_log_locked()
            self._append_activity(
                actor_id="codex",
                actor_label="Codex",
                actor_kind="agent",
                kind="prompt",
                title="Codex agent started",
                detail=prompt_text,
                status="pending",
                related_action="codex_job",
                prompt_id=prompt_id,
            )

        full_prompt = self._CODEX_PREAMBLE.replace("{prompt_id}", prompt_id) + prompt_text
        repo_root = self.paths.repo_root
        response_file = None
        job_key = None
        try:
            response_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", prefix=f"codex-{prompt_id}-",
                dir=str(self.paths.artifacts_root), delete=False,
            )
            response_path = response_file.name
            response_file.close()

            cmd = [
                str(codex_path),
                "exec",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                "--model", codex_model,
                "--cd", str(repo_root),
                "--add-dir", str(self.paths.asteria_root / "asteria_wiki"),
                "--add-dir", str(self.paths.asteria_root / "daemon"),
                "--add-dir", str(self.paths.asteria_root / "docs"),
                "-o", response_path,
                "-",
            ]

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(repo_root),
            )

            job_key = str(proc.pid)
            job_info: dict = {
                "prompt_id": prompt_id,
                "proc": proc,
                "model": codex_model,
                "started_at": utc_ts(),
                "output_tail": [],
            }
            with self._codex_jobs_lock:
                self._codex_jobs[job_key] = job_info

            if proc.stdin:
                proc.stdin.write(full_prompt)
                proc.stdin.close()

            timeout_sec = self._codex_timeout_minutes * 60

            def _read_output():
                assert proc.stdout is not None
                for line in proc.stdout:
                    stripped = line.rstrip("\n")
                    with self._codex_jobs_lock:
                        tail = job_info["output_tail"]
                        tail.append(stripped)
                        if len(tail) > 200:
                            job_info["output_tail"] = tail[-200:]

            reader = threading.Thread(target=_read_output, daemon=True)
            reader.start()

            # Poll every 3s instead of blocking on proc.wait(). This lets
            # us detect when the prompt has been resolved (Codex called
            # resolve-prompt via CLI) even if the process hasn't exited,
            # and kill it to avoid orphan processes.
            deadline = time.time() + timeout_sec
            resolved_externally = False
            while time.time() < deadline:
                rc = proc.poll()
                if rc is not None:
                    break
                with self._lock:
                    p = self._find_prompt_locked(prompt_id)
                    if p and p.status == "resolved":
                        resolved_externally = True
                        break
                time.sleep(3)
            else:
                # Timeout reached
                proc.kill()
                proc.wait(timeout=10)
                with self._lock:
                    p = self._find_prompt_locked(prompt_id)
                    if p and p.status != "resolved":
                        p.forward_status = "failed"
                        p.forward_error = f"codex timed out after {self._codex_timeout_minutes}m"
                        self._save_prompt_log_locked()
                return

            if resolved_externally:
                # Codex resolved the prompt via CLI but may still be running.
                # Give it a few seconds to exit gracefully, then force-kill.
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                reader.join(timeout=3)
                return

            reader.join(timeout=5)

            response_text = ""
            try:
                response_text = Path(response_path).read_text(encoding="utf-8").strip()
            except Exception:
                pass

            if not response_text:
                with self._codex_jobs_lock:
                    tail = job_info.get("output_tail", [])
                if tail:
                    response_text = "\n".join(tail[-50:])

            if proc.returncode == 0:
                # Only auto-resolve if Codex didn't already do it via CLI.
                with self._lock:
                    p = self._find_prompt_locked(prompt_id)
                    already_resolved = p is not None and p.status == "resolved"
                if not already_resolved:
                    self.resolve_prompt({
                        "prompt_id": prompt_id,
                        "response": response_text or "Codex agent completed (no output captured).",
                        "holder_id": "codex",
                        "holder_label": "Codex",
                        "holder_kind": "agent",
                    })
            else:
                with self._lock:
                    p = self._find_prompt_locked(prompt_id)
                    already_resolved = p is not None and p.status == "resolved"
                if not already_resolved:
                    with self._codex_jobs_lock:
                        tail = job_info.get("output_tail", [])
                    error_detail = "\n".join(tail[-10:]) if tail else f"exit code {proc.returncode}"
                    with self._lock:
                        p = self._find_prompt_locked(prompt_id)
                        if p:
                            p.forward_status = "failed"
                            p.forward_error = error_detail[:500]
                            self._save_prompt_log_locked()
                    self._append_activity(
                        actor_id="codex",
                        actor_label="Codex",
                        actor_kind="agent",
                        kind="prompt",
                        title="Codex agent failed",
                        detail=error_detail[:500],
                        status="warning",
                        related_action="codex_job",
                        prompt_id=prompt_id,
                    )

        except Exception as exc:
            with self._lock:
                p = self._find_prompt_locked(prompt_id)
                if p:
                    p.forward_status = "failed"
                    p.forward_error = str(exc)
                    self._save_prompt_log_locked()
        finally:
            # Ensure the process is dead no matter what path we took.
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except Exception:
                    pass
            if response_file:
                try:
                    Path(response_file.name).unlink(missing_ok=True)
                except Exception:
                    pass
            if job_key:
                with self._codex_jobs_lock:
                    info = self._codex_jobs.get(job_key)
                    if info:
                        info["proc"] = None
                    # Purge finished jobs older than 5 minutes to avoid buildup.
                    stale = [
                        k for k, v in self._codex_jobs.items()
                        if v.get("proc") is None and k != job_key
                    ]
                    for k in stale:
                        del self._codex_jobs[k]

    def list_prompts(self, payload: dict[str, Any]) -> dict[str, Any]:
        pending_only = bool(payload.get("pending_only", True))
        try:
            limit = int(payload.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))
        with self._lock:
            pending_total = len(self._pending_prompts_locked())
            items = self._pending_prompts_locked() if pending_only else list(self.prompt_log)
            selected = list(reversed(items[-limit:]))
            return {
                "ok": True,
                "items": [entry.as_dict() for entry in selected],
                "count": len(selected),
                "pending_only": pending_only,
                "pending_total": pending_total,
                **self.status(),
            }

    def log_note(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = str(payload.get("message", "")).strip()
        if not message:
            return {"ok": False, "error": "message is required", **self.status()}
        actor = self._actor_from_payload(payload)
        title = str(payload.get("title", "")).strip() or "Note posted"
        level = str(payload.get("level", "info")).strip().lower() or "info"
        with self._lock:
            self._append_activity(
                actor_id=actor["actor_id"],
                actor_label=actor["actor_label"],
                actor_kind=actor["actor_kind"],
                kind="note",
                title=title,
                detail=message,
                status=level,
                related_action="log_note",
            )
        return {"ok": True, "message": "note logged", **self.status()}

    def resolve_prompt(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_id = str(payload.get("prompt_id", "")).strip()
        if not prompt_id:
            return {"ok": False, "error": "prompt_id is required", **self.status()}
        response = str(payload.get("response", "")).strip() or None
        actor = self._actor_from_payload(payload)
        with self._lock:
            target = self._find_prompt_locked(prompt_id)
            if target is None:
                return {"ok": False, "error": f"prompt not found: {prompt_id}", **self.status()}
            target.status = "resolved"
            target.response = response
            target.resolved_at = utc_ts()
            target.resolved_by = actor["actor_id"]
            target.resolved_label = actor["actor_label"]
            self._save_prompt_log_locked()
            self._append_memory_note_locked(
                f"Asteria desk prompt resolved by {actor['actor_label']}: {target.id} - {response or target.text}"
            )
            self._append_activity(
                actor_id=actor["actor_id"],
                actor_label=actor["actor_label"],
                actor_kind=actor["actor_kind"],
                kind="prompt",
                title="Prompt resolved",
                detail=response or target.text,
                status="ok",
                related_action="resolve_prompt",
                prompt_id=target.id,
            )
        return {"ok": True, "message": "prompt resolved", "prompt": target.as_dict(), **self.status()}

    def retry_prompt_forward(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_id = str(payload.get("prompt_id", "")).strip()
        if not prompt_id:
            return {"ok": False, "error": "prompt_id is required", **self.status()}
        return self._queue_prompt_forward(prompt_id, retry=True)

    def _start_loop(self) -> None:
        if self._loop is not None:
            return
        loop = asyncio.new_event_loop()

        def runner() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=runner, name="asteria-runtime-loop", daemon=True)
        thread.start()
        self._loop = loop
        self._loop_thread = thread

    def _stop_loop(self) -> None:
        if self._loop is None:
            return
        loop = self._loop
        thread = self._loop_thread
        self._loop = None
        self._loop_thread = None
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=2.0)

    def _ensure_robot_thread(self) -> None:
        if self._robot_thread is not None and self._robot_thread.is_alive():
            return

        def runner() -> None:
            while True:
                item = self._robot_task_queue.get()
                if item is None:
                    return
                func, result_queue = item
                try:
                    result_queue.put(("ok", func()))
                except BaseException as exc:
                    result_queue.put(("exc", exc, traceback.format_exc()))

        self._robot_thread = threading.Thread(target=runner, name="asteria-robot-worker", daemon=True)
        self._robot_thread.start()

    def _run_on_robot_thread(self, func: Any) -> Any:
        if self._robot_thread is not None and threading.current_thread() is self._robot_thread:
            return func()
        self._ensure_robot_thread()
        result_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._robot_task_queue.put((func, result_queue))
        kind, *payload = result_queue.get()
        if kind == "ok":
            return payload[0]
        exc, tb = payload
        if isinstance(exc, BaseException):
            exc.__notes__ = [tb]
            raise exc
        raise RuntimeError(tb)

    def _stop_robot_thread(self) -> None:
        thread = self._robot_thread
        self._robot_thread = None
        self._robot_task_queue.put(None)
        if thread is not None:
            thread.join(timeout=2.0)

    def _load_runtime(self) -> str | None:
        if self._aim_fsm is not None:
            return None
        try:
            import aim_fsm  # type: ignore
            import vex  # type: ignore
            from aim_fsm import evbase, pilot  # type: ignore
            from aim_fsm.events import SpeechEvent, TextMsgEvent  # type: ignore
            from aim_fsm.program import StateMachineProgram  # type: ignore
        except Exception as exc:
            self._runtime_error = str(exc)
            self.telemetry.runtime_error = self._runtime_error
            self._set_error(f"runtime import failed: {exc}")
            return self._runtime_error
        self._aim_fsm = aim_fsm
        self._aim_program = aim_fsm.program
        self._evbase = evbase
        self._pilot = pilot
        self._state_machine_program_cls = StateMachineProgram
        self._text_event_cls = TextMsgEvent
        self._speech_event_cls = SpeechEvent
        self._vex = vex
        self._aim_transport = aim_fsm.aim
        self._configure_headless_runtime()
        self._runtime_error = ""
        self.telemetry.runtime_error = ""
        return None

    def _configure_headless_runtime(self) -> None:
        if self._aim_fsm is None or self._aim_program is None:
            return
        for owner in (self._aim_fsm, self._aim_program):
            setattr(owner, "CamViewer", HeadlessViewerStub)
            setattr(owner, "WorldMapViewer", HeadlessViewerStub)
            setattr(owner, "ParticleViewer", HeadlessViewerStub)
            setattr(owner, "PathViewer", HeadlessViewerStub)

    def _stop_running_fsm_locked(self) -> dict[str, Any]:
        if self._aim_program is None:
            return {"unloaded": False, "fsm_name": None}
        running = self._aim_program.running_fsm
        if running is None:
            self._aim_program.running_fsm = None
            return {"unloaded": False, "fsm_name": None}

        fsm_name = getattr(running, "name", None) or running.__class__.__name__

        def stop_running() -> None:
            stop_fn = getattr(running, "stop", None)
            if callable(stop_fn):
                stop_fn()

        loop = getattr(getattr(running, "robot", None), "loop", None)
        if loop is not None and hasattr(loop, "call_soon_threadsafe") and self._loop_thread is not None and threading.current_thread() is not self._loop_thread:
            done = threading.Event()
            outcome: dict[str, BaseException] = {}

            def runner() -> None:
                try:
                    stop_running()
                except BaseException as exc:
                    outcome["error"] = exc
                finally:
                    done.set()

            loop.call_soon_threadsafe(runner)
            done.wait(timeout=1.5)
            error = outcome.get("error")
            if error is not None:
                raise error
        else:
            stop_running()

        self._aim_program.running_fsm = None
        return {"unloaded": True, "fsm_name": fsm_name}

    def _reset_runtime_globals_locked(self) -> None:
        if self._evbase is not None:
            self._evbase.robot_for_loading = None
        if self._pilot is not None:
            self._pilot.pilot_global_doorpass_node = None

    def _append_connection_diagnostic(self, host: str, runtime_mode: str, ok: bool, error: str | None = None) -> None:
        item: dict[str, Any] = {
            "timestamp": utc_ts(),
            "host": host,
            "runtime_mode": runtime_mode,
            "ok": ok,
        }
        if error:
            item["error"] = error
        items = list(self.connection_diagnostics.get("items", []))
        items.append(item)
        self.connection_diagnostics = {
            "timestamp": item["timestamp"],
            "items": items[-20:],
        }

    def _register_connected_robot_locked(self, robot: Any, host: str) -> None:
        self.robot = robot
        self.connected_host = host
        self.connected_runtime_mode = getattr(robot, "runtime_mode", "unknown")
        if self._evbase is not None:
            self._evbase.robot_for_loading = robot
        if self._pilot is not None:
            self._pilot.pilot_global_doorpass_node = self._pilot.DoorPass()
        self._refresh_telemetry_locked()
        self.last_error = ""
        self.telemetry.last_error = ""

    def _cleanup_robot(self) -> None:
        try:
            self._stop_running_fsm_locked()
        except Exception:
            pass
        if self.robot is not None:
            try:
                self.robot.robot0.stop_all_movement()
            except Exception:
                pass
            self._shutdown_robot_transport(self.robot.robot0)
            try:
                self.robot.robot0.exit_handler()
            except Exception:
                pass
        self.robot = None
        self.connected_host = None
        self.connected_runtime_mode = None
        self.telemetry.connected = False
        self.telemetry.host = None
        self.telemetry.battery_pct = None
        self.telemetry.pose = {}
        self._reset_runtime_globals_locked()

    def _shutdown_robot_transport(self, robot0: Any) -> None:
        if robot0 is None:
            return

        img_thread = getattr(robot0, "_ws_img_thread", None)
        if img_thread is not None:
            try:
                img_thread.stop_stream()
            except Exception:
                pass

        for attr in ("_ws_cmd_thread", "_ws_status_thread", "_ws_img_thread", "_ws_audio_thread"):
            thread = getattr(robot0, attr, None)
            if thread is None:
                continue
            try:
                thread.running = False
            except Exception:
                pass
            try:
                thread.ws_close()
            except Exception:
                pass

        for attr in ("_ws_cmd_thread", "_ws_status_thread", "_ws_img_thread", "_ws_audio_thread"):
            thread = getattr(robot0, attr, None)
            if thread is None:
                continue
            try:
                thread.join(timeout=0.5)
            except Exception:
                pass

    def _assert_connected(self) -> str | None:
        if self.robot is None:
            return "not connected"
        return None

    def _get_robot0_pose(self) -> dict[str, Any]:
        if self.robot is None:
            return {}
        robot0 = getattr(self.robot, "robot0", None)
        if robot0 is None:
            return {}

        def call(name: str, fallback_name: str | None = None) -> Any:
            target = getattr(robot0, name, None)
            if callable(target):
                return target()
            if fallback_name:
                fallback = getattr(robot0, fallback_name, None)
                if callable(fallback):
                    return fallback()
            return None

        x = call("get_x_position", "get_x")
        y = call("get_y_position", "get_y")
        heading = call("get_heading")
        if x is None and y is None and heading is None:
            return {}
        return {"x": x, "y": y, "heading": heading}

    def _build_minimal_robot(self, host: str) -> MinimalAsteriaRobot:
        if self._aim_transport is None:
            raise RuntimeError("aim transport not loaded")
        robot0 = self._construct_robot_without_signal_handlers(lambda: self._aim_transport.Robot(host=host))
        return MinimalAsteriaRobot(robot0)

    def _build_full_robot(self, host: str) -> Any:
        if self._aim_fsm is None or self._loop is None:
            raise RuntimeError("aim_fsm runtime not loaded")
        robot = self._construct_robot_without_signal_handlers(
            lambda: self._aim_fsm.Robot(loop=self._loop, host=host, launch_speech_listener=self.enable_speech)
        )
        robot.runtime_mode = "aim_fsm_headless"
        robot.supports_fsm = True
        robot.get_camera_image = robot.robot0.get_camera_image
        if getattr(robot, "particle_filter", None) is None:
            robot.particle_filter = HeadlessParticleFilterStub(robot)
        return robot

    def _construct_robot_without_signal_handlers(self, factory: Any) -> Any:
        if threading.current_thread() is threading.main_thread():
            return factory()

        original_signal = signal.signal

        def noop_signal(*_args: Any, **_kwargs: Any) -> Any:
            return None

        signal.signal = noop_signal
        try:
            return factory()
        finally:
            signal.signal = original_signal

    def _load_fsm_module(self, module_name: str) -> Any:
        module = sys.modules.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)
        else:
            module = importlib.reload(module)
        self._fsm_modules[module_name] = module
        return module

    def _resolve_fsm_class(self, module_name: str, module: Any) -> type[Any]:
        candidates = [module_name, class_name_for(module_name)]
        state_machine_cls = self._state_machine_program_cls
        if state_machine_cls is None:
            raise RuntimeError("StateMachineProgram is not loaded")

        for candidate_name in candidates:
            candidate = getattr(module, candidate_name, None)
            if isinstance(candidate, type) and issubclass(candidate, state_machine_cls):
                return candidate

        for _name, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is state_machine_cls:
                continue
            if candidate.__module__ != module.__name__:
                continue
            if issubclass(candidate, state_machine_cls):
                return candidate

        raise RuntimeError(f"module {module_name} does not define a StateMachineProgram")

    def _instantiate_fsm_program(self, fsm_cls: type[Any]) -> Any:
        kwargs = {
            "launch_cam_viewer": False,
            "launch_worldmap_viewer": False,
            "launch_particle_viewer": False,
            "launch_path_viewer": False,
            "speech": self.enable_speech,
        }
        try:
            signature = inspect.signature(fsm_cls.__init__)
        except (TypeError, ValueError):
            signature = None

        init_kwargs = kwargs
        if signature is not None:
            parameters = signature.parameters
            accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values())
            init_kwargs = {
                name: value
                for name, value in kwargs.items()
                if accepts_kwargs or name in parameters
            }

        return fsm_cls(**init_kwargs)

    def _run_fsm_module_locked(self, module_name: str) -> Any:
        if self._evbase is None or self._aim_program is None:
            raise RuntimeError("aim_fsm runtime not loaded")
        if self.robot is None:
            raise RuntimeError("not connected")

        self._stop_running_fsm_locked()
        self._evbase.robot_for_loading = self.robot

        module = self._load_fsm_module(module_name)
        module.robot = self._evbase.robot_for_loading
        fsm_cls = self._resolve_fsm_class(module_name, module)
        running = self._instantiate_fsm_program(fsm_cls)
        self._aim_program.running_fsm = running
        running.robot.loop.call_soon_threadsafe(running.start)
        return running

    def _refresh_telemetry_locked(self) -> None:
        if self.robot is None:
            self.telemetry.connected = False
            self.telemetry.host = None
            self.telemetry.battery_pct = None
            self.telemetry.pose = {}
            return
        self.telemetry.connected = True
        self.telemetry.host = self.connected_host
        try:
            self.telemetry.battery_pct = self.robot.robot0.get_battery_capacity()
        except Exception:
            self.telemetry.battery_pct = None
        try:
            self.telemetry.pose = self._get_robot0_pose()
        except Exception:
            self.telemetry.pose = {}

    def _refresh_lease(self, holder_id: str | None = None) -> None:
        if holder_id and self.lease.holder_id != holder_id:
            return
        self.lease.expires_at_epoch = time.time() + self.lease_timeout_sec

    def _new_unclaimed_lease(self) -> ControlLease:
        return ControlLease(expires_at_epoch=0.0)

    def _lease_active(self) -> bool:
        return bool(self.lease.holder_id) and self.lease.expires_at_epoch > time.time()

    def _priority_for_holder_kind(self, holder_kind: str) -> int:
        normalized = str(holder_kind).strip().lower()
        if normalized == "human":
            return 100
        if normalized == "agent":
            return 50
        return 0

    def _claim_allowed(self, holder_id: str, holder_kind: str, force: bool) -> bool:
        if not holder_id:
            return False
        if not self._lease_active():
            return True
        if holder_id == self.lease.holder_id:
            return True

        current_kind = str(self.lease.holder_kind).strip().lower()
        requested_kind = str(holder_kind).strip().lower()
        current_priority = self._priority_for_holder_kind(current_kind)
        requested_priority = self._priority_for_holder_kind(requested_kind)

        if current_kind == "human" and requested_kind != "human":
            return False
        if requested_kind == "human":
            return current_kind != "human" or force
        if requested_priority > current_priority:
            return True
        return force and current_kind != "human"

    def claim_lease(self, payload: dict[str, Any]) -> dict[str, Any]:
        holder_id = str(payload.get("holder_id", "local-gui")).strip() or "local-gui"
        holder_label = str(payload.get("holder_label", holder_id)).strip() or holder_id
        holder_kind = str(payload.get("holder_kind", "human")).strip() or "human"
        force = bool(payload.get("force", False))
        with self._lock:
            if not self._claim_allowed(holder_id, holder_kind, force):
                return {
                    "ok": False,
                    "error": f"lease currently held by {self.lease.holder_label} ({self.lease.holder_kind})",
                    "lease": self.lease.as_dict(),
                }
            self.lease.holder_id = holder_id
            self.lease.holder_label = holder_label
            self.lease.holder_kind = holder_kind
            self.lease.priority = self._priority_for_holder_kind(holder_kind)
            self._refresh_lease(holder_id)
            return {"ok": True, "lease": self.lease.as_dict()}

    def release_lease(self, payload: dict[str, Any]) -> dict[str, Any]:
        holder_id = str(payload.get("holder_id", "")).strip()
        with self._lock:
            if holder_id and holder_id != self.lease.holder_id:
                return {"ok": False, "error": "cannot release another controller lease", "lease": self.lease.as_dict()}
            self.lease = self._new_unclaimed_lease()
            return {"ok": True, "lease": self.lease.as_dict()}

    def _require_lease(self, payload: dict[str, Any]) -> str | None:
        holder_id = str(payload.get("holder_id", "")).strip()
        if not holder_id:
            return "holder_id is required"
        if not self.lease.holder_id:
            return "control lease not claimed"
        if time.time() > self.lease.expires_at_epoch:
            return "control lease expired"
        if holder_id != self.lease.holder_id:
            return f"lease held by {self.lease.holder_label}"
        self._refresh_lease(holder_id)
        return None

    def status(self) -> dict[str, Any]:
        with self._lock:
            running = None
            if self._aim_fsm is not None:
                running = self._aim_fsm.program.running_fsm
            self.telemetry.connected = self.robot is not None
            self.telemetry.host = self.connected_host
            self.telemetry.running_fsm_name = getattr(running, "name", None) if running else None
            self.telemetry.running_fsm_active = bool(running and getattr(running, "running", False))
            pending_prompts = [entry.as_dict() for entry in self._pending_prompts_locked()]
            return {
                "timestamp": utc_ts(),
                "uptime_sec": round(time.time() - self.started_at, 2),
                "telemetry": self.telemetry.as_dict(),
                "lease": self.lease.as_dict(),
                "connection": self._connection_state(),
                "bridge": self._bridge_state(),
                "safe_limits": {
                    "max_move_mm": self.safe_max_move_mm,
                    "max_turn_deg": self.safe_max_turn_deg,
                },
                "last_result": self.last_result,
                "last_action": self.command_log[-1]["action"] if self.command_log else None,
                "latest_image": self.latest_image_summary(),
                "pending_prompt_count": len(pending_prompts),
                "latest_pending_prompt": pending_prompts[-1] if pending_prompts else None,
                "activities": [entry.as_dict() for entry in self.activity_log[-40:]],
                "prompts": [entry.as_dict() for entry in self.prompt_log[-40:]],
                "paths": {
                    "repo_root": str(self.paths.repo_root),
                    "asteria_root": str(self.paths.asteria_root),
                    "fsm_root": str(self.paths.fsm_root),
                    "image_root": str(self.paths.image_root),
                    "run_root": str(self.paths.run_root),
                },
                "recent_commands": self.command_log[-20:],
                "fsm_files": list_fsm_files(self.paths).get("items", []),
                "codex_jobs": self._codex_jobs_summary(),
                "codex_model": self._codex_model(),
                "codex_timeout_minutes": self._codex_timeout_minutes,
                "recent_errors": self._error_log[-10:],
            }

    def connect(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._load_runtime():
            return {"ok": False, "error": self._runtime_error, **self.status()}
        with self._lock:
            if self.robot is not None:
                return {"ok": True, "message": "already connected", **self.status()}

        timeout = float(payload.get("retry_max_sec") or self.retry_max_sec)
        attempted_hosts = self._candidate_hosts(str(payload.get("host", "")).strip() or None)
        self.last_connect_attempt_at = utc_ts()
        self.last_connect_attempt_hosts = attempted_hosts
        self.connection_diagnostics = {"timestamp": self.last_connect_attempt_at, "items": []}
        deadline = time.monotonic() + max(timeout, 1.0)
        last_exc: BaseException | None = None
        builders: list[tuple[str, Any]] = [
            ("aim_fsm_headless", self._build_full_robot),
            ("aim_raw_minimal", self._build_minimal_robot),
        ]
        while time.monotonic() < deadline:
            for host in attempted_hosts:
                if time.monotonic() >= deadline:
                    break
                for runtime_mode, builder in builders:
                    if time.monotonic() >= deadline:
                        break
                    try:
                        with self._lock:
                            self._start_loop()
                            self._cleanup_robot()
                            robot = builder(host)
                            self._register_connected_robot_locked(robot, host)
                            self._append_connection_diagnostic(host, runtime_mode, True)
                            return {
                                "ok": True,
                                "message": f"connected to {host} using {self.connected_runtime_mode}",
                                **self.status(),
                            }
                    except BaseException as exc:
                        last_exc = exc
                        error_text = str(exc) or exc.__class__.__name__
                        with self._lock:
                            self._append_connection_diagnostic(host, runtime_mode, False, error_text)
                            self._set_error(f"connect failed for {host} via {runtime_mode}: {error_text}")
                            self._cleanup_robot()
                if time.monotonic() >= deadline:
                    break
            time.sleep(1.0)
        message = f"failed to connect after {timeout}s"
        if last_exc is not None:
            message = f"{message}: {last_exc}"
        with self._lock:
            self._set_error(message)
        return {"ok": False, "error": message, **self.status()}

    def disconnect(self) -> dict[str, Any]:
        with self._lock:
            self._cleanup_robot()
            self._stop_loop()
            return {"ok": True, "message": "disconnected", **self.status()}

    def reconnect(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.disconnect()
        return self.connect(payload)

    def run_fsm(self, payload: dict[str, Any]) -> dict[str, Any]:
        module = slugify(str(payload.get("module", "")).strip())
        if not module:
            return {"ok": False, "error": "module is required", **self.status()}
        source_path = self.paths.fsm_root / f"{module}.fsm"
        generated_path = source_path.with_suffix(".py")
        compile_result = {
            "ok": True,
            "generated_py": str(generated_path),
            "generated_exists": generated_path.exists(),
            "compiled_now": False,
            "up_to_date": generated_path.exists(),
        }
        if source_path.exists() or generated_path.exists():
            compile_result = ensure_compiled_fsm(self.paths, name=module, fsm_path=source_path)
            if not compile_result.get("ok"):
                return {**compile_result, **self.status()}
        if self._load_runtime():
            return {**compile_result, "ok": False, "error": self._runtime_error, **self.status()}
        with self._lock:
            if self._assert_connected():
                return {**compile_result, "ok": False, "error": "not connected", **self.status()}
            if not getattr(self.robot, "supports_fsm", False):
                return {
                    **compile_result,
                    "ok": False,
                    "error": "live FSM execution is unavailable on the minimal AIM runtime",
                    **self.status(),
                }
            try:
                running = self._run_fsm_module_locked(module)
            except Exception as exc:
                self._set_error(f"runfsm failed: {exc}")
                return {**compile_result, "ok": False, "error": str(exc), "traceback": traceback.format_exc(), **self.status()}
        artifact_dir = write_run_artifact(self.paths, "runfsm", {"module": module, "status": self.status()})
        return {
            "ok": True,
            "message": f"runfsm started for {module}",
            "fsm_name": getattr(running, "name", module) if running else module,
            "artifact_dir": artifact_dir,
            "generated_py": compile_result.get("generated_py"),
            "generated_exists": compile_result.get("generated_exists"),
            "compiled_now": compile_result.get("compiled_now", False),
            **self.status(),
        }

    def send_text(self, payload: dict[str, Any], speech: bool = False) -> dict[str, Any]:
        if self._load_runtime():
            return {"ok": False, "error": self._runtime_error, **self.status()}
        message = str(payload.get("message", "")).strip()
        if not message:
            return {"ok": False, "error": "message is required", **self.status()}
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            if not getattr(self.robot, "supports_fsm", False):
                return {"ok": False, "error": "FSM event injection is unavailable on the minimal AIM runtime", **self.status()}
            running = self._aim_fsm.program.running_fsm
            if not running or not getattr(running, "running", False):
                return {"ok": False, "error": "no active fsm", **self.status()}
            event_cls = self._speech_event_cls if speech else self._text_event_cls
            try:
                running.robot.erouter.post(event_cls(message))
            except Exception as exc:
                self._set_error(f"event send failed: {exc}")
                return {"ok": False, "error": str(exc), "traceback": traceback.format_exc(), **self.status()}
        return {"ok": True, "message": "fsm event posted", **self.status()}

    def unload_fsm(self) -> dict[str, Any]:
        if self._load_runtime():
            return {"ok": False, "error": self._runtime_error, **self.status()}
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                result = self._stop_running_fsm_locked()
                self.robot.robot0.stop_all_movement()
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"unload_fsm failed: {exc}")
                return {"ok": False, "error": str(exc), "traceback": traceback.format_exc(), **self.status()}
        if result.get("unloaded"):
            return {
                "ok": True,
                "message": f"active fsm unloaded: {result.get('fsm_name')}",
                "fsm_name": result.get("fsm_name"),
                **self.status(),
            }
        return {"ok": True, "message": "no active fsm to unload", **self.status()}

    def stop_all(self, payload: dict[str, Any]) -> dict[str, Any]:
        stop_fsm = bool(payload.get("stop_fsm", True))
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            had_active_fsm = bool(self._aim_program is not None and self._aim_program.running_fsm is not None)
            unloaded = {"unloaded": False, "fsm_name": None}
            try:
                if stop_fsm:
                    unloaded = self._stop_running_fsm_locked()
                self.robot.robot0.stop_all_movement()
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"stop_all failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}

        if stop_fsm and unloaded.get("unloaded"):
            message = f"stop_all issued; active fsm unloaded: {unloaded.get('fsm_name')}"
        elif had_active_fsm:
            message = "stop_all issued; active fsm left loaded by operator preference"
        else:
            message = "stop_all issued"

        return {
            "ok": True,
            "message": message,
            "fsm_name": unloaded.get("fsm_name"),
            "stop_fsm": stop_fsm,
            "fsm_unloaded": bool(unloaded.get("unloaded")),
            **self.status(),
        }

    def capture_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                get_camera_image = getattr(self.robot, "get_camera_image", None)
                if callable(get_camera_image):
                    image_bytes = get_camera_image()
                else:
                    image_bytes = self.robot.robot0.get_camera_image()
            except Exception as exc:
                self._set_error(f"capture_image failed: {exc}")
                return {"ok": False, "error": str(exc), "traceback": traceback.format_exc(), **self.status()}

            if not image_bytes or image_bytes in {bytes(1), b"\x00"}:
                return {"ok": False, "error": "no image received", **self.status()}

            destination = payload.get("out_path")
            if destination:
                image_path = Path(str(destination)).expanduser()
                if not image_path.is_absolute():
                    image_path = self.paths.repo_root / image_path
            else:
                stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                image_path = self.paths.image_root / f"asteria-{stamp}.jpg"

            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(image_bytes)
            self.telemetry.last_image_path = str(image_path)
            self._refresh_telemetry_locked()
        return {"ok": True, "message": "image captured", "image_path": str(image_path), **self.status()}

    def create_fsm(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name:
            return {"ok": False, "error": "name is required", **self.status()}
        result = create_fsm_file(self.paths, name=name, content=payload.get("content"))
        return {**result, **self.status()}

    def compile_fsm(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = payload.get("fsm_path")
        if target:
            fsm_path = Path(str(target)).expanduser()
            if not fsm_path.is_absolute():
                fsm_path = self.paths.repo_root / fsm_path
        else:
            name = slugify(str(payload.get("name", "")).strip())
            if not name:
                return {"ok": False, "error": "name or fsm_path is required", **self.status()}
            fsm_path = self.paths.fsm_root / f"{name}.fsm"
        result = compile_fsm_file(self.paths, fsm_path)
        if result.get("ok"):
            result["artifact_dir"] = write_run_artifact(self.paths, "compile", result)
        return {**result, **self.status()}

    def move(self, payload: dict[str, Any]) -> dict[str, Any]:
        distance_mm = float(payload.get("distance_mm", 0.0))
        angle_deg = float(payload.get("angle_deg", 0.0))
        if abs(distance_mm) > self.safe_max_move_mm:
            return {"ok": False, "error": f"distance exceeds safe limit ({self.safe_max_move_mm} mm)", **self.status()}
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                self.robot.robot0.move_for(distance_mm, angle_deg, wait=False)
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"move failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}
        return {"ok": True, "message": "move command issued", **self.status()}

    def sideways(self, payload: dict[str, Any]) -> dict[str, Any]:
        distance_mm = float(payload.get("distance_mm", 0.0))
        return self.move({"distance_mm": abs(distance_mm), "angle_deg": 90.0 if distance_mm >= 0 else -90.0})

    def drive_at(self, payload: dict[str, Any]) -> dict[str, Any]:
        angle_deg = float(payload.get("angle_deg", 0.0))
        speed_pct = max(0.0, min(100.0, abs(float(payload.get("speed_pct", 0.0)))))
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                self.robot.robot0.move_at(angle_deg, speed_pct)
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"drive_at failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}
        return {"ok": True, "message": "continuous drive updated", **self.status()}

    def turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        angle_deg = float(payload.get("angle_deg", 0.0))
        if abs(angle_deg) > self.safe_max_turn_deg:
            return {"ok": False, "error": f"turn exceeds safe limit ({self.safe_max_turn_deg} deg)", **self.status()}
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                # Pass the signed angle directly so left/right do not depend on cross-module enum identity.
                self.robot.robot0.turn_for(self._vex.TurnType.RIGHT, angle_deg, wait=False)
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"turn failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}
        return {"ok": True, "message": "turn command issued", **self.status()}

    def turn_at(self, payload: dict[str, Any]) -> dict[str, Any]:
        turn_rate_pct = max(-100.0, min(100.0, float(payload.get("turn_rate_pct", 0.0))))
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                # Use the RIGHT enum with a signed rate so left/right do not depend on enum identity across modules.
                self.robot.robot0.turn(self._vex.TurnType.RIGHT, turn_rate_pct)
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"turn_at failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}
        return {"ok": True, "message": "continuous turn updated", **self.status()}

    def say(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", "")).strip()
        if not text:
            return {"ok": False, "error": "text is required", **self.status()}
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                render_screen_text(self.robot.robot0.screen, self._vex, text)
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"display text failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}
        return {"ok": True, "message": "screen text displayed", **self.status()}

    def kick(self, payload: dict[str, Any]) -> dict[str, Any]:
        style = str(payload.get("style", "medium")).strip().lower() or "medium"
        if self._vex is None:
            return {"ok": False, "error": "not connected", **self.status()}
        kick_map = {
            "soft": self._vex.KickType.SOFT,
            "medium": self._vex.KickType.MEDIUM,
            "hard": self._vex.KickType.HARD,
        }
        if style not in kick_map:
            return {"ok": False, "error": "style must be one of soft, medium, hard", **self.status()}
        with self._lock:
            if self._assert_connected():
                return {"ok": False, "error": "not connected", **self.status()}
            try:
                self.robot.robot0.kick(kick_map[style])
                self._refresh_telemetry_locked()
            except Exception as exc:
                self._set_error(f"kick failed: {exc}")
                return {"ok": False, "error": str(exc), **self.status()}
        return {"ok": True, "message": f"{style} kick issued", **self.status()}

    def dispatch(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._record(action, payload)
        if action == "status":
            return self._remember_result({"ok": True, "message": "status refreshed"})
        if action == "lease_claim":
            return self._remember_result(self.claim_lease(payload))
        if action == "lease_release":
            return self._remember_result(self.release_lease(payload))
        if action == "connect":
            return self._remember_result(self.connect(payload))
        if action == "disconnect":
            return self._remember_result(self.disconnect())
        if action == "reconnect":
            return self._remember_result(self.reconnect(payload))
        if action == "set_connection_config":
            return self._remember_result(self.configure_connection(payload))
        if action == "save_profile_robot_target":
            return self._remember_result(self.save_profile_robot_target(payload))
        if action == "diagnose_connection":
            return self._remember_result(self.diagnose_connection(payload))
        if action == "submit_prompt":
            return self._remember_result(self.submit_prompt(payload))
        if action == "log_note":
            return self._remember_result(self.log_note(payload))
        if action == "list_prompts":
            return self._remember_result(self.list_prompts(payload))
        if action == "resolve_prompt":
            return self._remember_result(self.resolve_prompt(payload))
        if action == "retry_prompt_forward":
            return self._remember_result(self.retry_prompt_forward(payload))
        if action == "kill_codex_job":
            return self._remember_result(self.kill_codex_job(payload))
        if action == "get_codex_output":
            return self._remember_result(self.get_codex_output(payload))
        if action == "set_codex_timeout":
            return self._remember_result(self.set_codex_timeout(payload))
        if action == "get_error_log":
            return self._remember_result(self.get_error_log(payload))
        if action == "create_fsm":
            return self._remember_result(self.create_fsm(payload))
        if action == "compile_fsm":
            return self._remember_result(self.compile_fsm(payload))

        lease_error = self._require_lease(payload)
        if lease_error:
            return self._remember_result({"ok": False, "error": lease_error, **self.status()})

        if action == "run_fsm":
            return self._remember_result(self.run_fsm(payload))
        if action == "unload_fsm":
            return self._remember_result(self.unload_fsm())
        if action == "send_text":
            return self._remember_result(self.send_text(payload, speech=False))
        if action == "send_speech":
            return self._remember_result(self.send_text(payload, speech=True))
        if action == "stop_all":
            return self._remember_result(self.stop_all(payload))
        if action == "capture_image":
            return self._remember_result(self.capture_image(payload))
        if action == "move":
            return self._remember_result(self.move(payload))
        if action == "sideways":
            return self._remember_result(self.sideways(payload))
        if action == "turn":
            return self._remember_result(self.turn(payload))
        if action == "drive_at":
            return self._remember_result(self.drive_at(payload))
        if action == "turn_at":
            return self._remember_result(self.turn_at(payload))
        if action == "say":
            return self._remember_result(self.say(payload))
        if action == "kick":
            return self._remember_result(self.kick(payload))
        if action == "shutdown":
            self.shutdown_event.set()
            self.disconnect()
            return self._remember_result({"ok": True, "message": "asteria shutting down", **self.status()})
        return self._remember_result({"ok": False, "error": f"unknown action: {action}", **self.status()})
