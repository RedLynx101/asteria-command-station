from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        return default


def _join_url(base_url: str, path: str) -> str:
    normalized_base = str(base_url or "").strip().rstrip("/")
    normalized_path = f"/{str(path or '').strip().lstrip('/')}"
    return f"{normalized_base}{normalized_path}"


def _short_body(body: str, limit: int = 240) -> str:
    text = " ".join(str(body or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _response_id_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    response_id = (
        payload.get("id")
        or payload.get("response_id")
        or (payload.get("response") or {}).get("id")
    )
    text = str(response_id or "").strip()
    return text or None


def _response_status_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    response = payload.get("response")
    if isinstance(response, dict):
        text = str(response.get("status") or "").strip()
        if text:
            return text
    text = str(payload.get("status") or "").strip()
    return text or None


def _response_error_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    response = payload.get("response")
    if isinstance(response, dict):
        error = response.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or error.get("type") or "").strip()
            if message:
                return message
        text = str(response.get("error") or "").strip()
        if text:
            return text
    error = payload.get("error")
    if isinstance(error, dict):
        message = str(error.get("message") or error.get("type") or "").strip()
        if message:
            return message
    text = str(error or "").strip()
    return text or None


@dataclass
class OpenClawBridgeConfig:
    enabled: bool = False
    gateway_url: str = "http://127.0.0.1:18889"
    gateway_path: str = "/v1/responses"
    health_path: str = "/health"
    gateway_token: str | None = None
    session_key: str = "session:asteria-desk"
    session_key_template: str | None = "{base_session_key}:{prompt_id}"
    timeout_ms: int = 120000
    model: str = "openclaw/default"
    user: str = "asteria-desk-bridge"
    session_header: str = "X-OpenClaw-Session-Key"
    auto_start: bool = True
    auto_start_command: str = "openclaw gateway"
    auto_start_timeout_ms: int = 20000

    @classmethod
    def from_env(cls) -> "OpenClawBridgeConfig":
        return cls(
            enabled=_env_bool("ASTERIA_OPENCLAW_BRIDGE_ENABLED", False),
            gateway_url=str(os.getenv("ASTERIA_OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18889")).strip() or "http://127.0.0.1:18889",
            gateway_path=str(os.getenv("ASTERIA_OPENCLAW_GATEWAY_PATH", "/v1/responses")).strip() or "/v1/responses",
            health_path=str(os.getenv("ASTERIA_OPENCLAW_HEALTH_PATH", "/health")).strip() or "/health",
            gateway_token=str(os.getenv("ASTERIA_OPENCLAW_GATEWAY_TOKEN", "")).strip() or None,
            session_key=str(os.getenv("ASTERIA_OPENCLAW_SESSION_KEY", "session:asteria-desk")).strip() or "session:asteria-desk",
            session_key_template=str(os.getenv("ASTERIA_OPENCLAW_SESSION_KEY_TEMPLATE", "{base_session_key}:{prompt_id}")).strip() or None,
            timeout_ms=max(1000, _env_int("ASTERIA_OPENCLAW_BRIDGE_TIMEOUT_MS", 120000)),
            model=str(os.getenv("ASTERIA_OPENCLAW_BRIDGE_MODEL", "openclaw/default")).strip() or "openclaw/default",
            user=str(os.getenv("ASTERIA_OPENCLAW_BRIDGE_USER", "asteria-desk-bridge")).strip() or "asteria-desk-bridge",
            session_header=str(os.getenv("ASTERIA_OPENCLAW_SESSION_HEADER", "X-OpenClaw-Session-Key")).strip() or "X-OpenClaw-Session-Key",
            auto_start=_env_bool("ASTERIA_OPENCLAW_AUTO_START", True),
            auto_start_command=str(os.getenv("ASTERIA_OPENCLAW_START_COMMAND", "openclaw gateway")).strip() or "openclaw gateway",
            auto_start_timeout_ms=max(1000, _env_int("ASTERIA_OPENCLAW_AUTO_START_TIMEOUT_MS", 20000)),
        )

    @property
    def endpoint_url(self) -> str:
        return _join_url(self.gateway_url, self.gateway_path)

    @property
    def health_url(self) -> str:
        return _join_url(self.gateway_url, self.health_path)

    def public_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("gateway_token", None)
        payload["endpoint_url"] = self.endpoint_url
        payload["health_url"] = self.health_url
        payload.pop("auto_start_command", None)
        return payload


@dataclass
class OpenClawBridgeResult:
    ok: bool
    attempted: bool
    accepted: bool = False
    status_code: int | None = None
    response_id: str | None = None
    error: str | None = None
    response_body: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class OpenClawBridgeClient:
    def __init__(self, config: OpenClawBridgeConfig) -> None:
        self.config = config
        self._start_lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "OpenClawBridgeClient":
        return cls(OpenClawBridgeConfig.from_env())

    def session_key_for_prompt(self, prompt_id: str) -> str:
        template = str(self.config.session_key_template or "").strip()
        if not template:
            return self.config.session_key

        rendered = (
            template.replace("{prompt_id}", str(prompt_id or "").strip())
            .replace("{base_session_key}", self.config.session_key)
        ).strip()
        return rendered or self.config.session_key

    def _health_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "asteria-openclaw-bridge/1",
        }
        if self.config.gateway_token:
            headers["Authorization"] = f"Bearer {self.config.gateway_token}"
        return headers

    def _gateway_is_healthy(self, timeout_sec: float = 2.0) -> bool:
        request = urllib.request.Request(
            url=self.config.health_url,
            method="GET",
            headers=self._health_headers(),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                return int(getattr(response, "status", 200)) < 500
        except urllib.error.HTTPError as exc:
            return exc.code in {200, 204, 401, 403}
        except Exception:
            return False

    def _start_command_argv(self) -> list[str]:
        raw = str(self.config.auto_start_command or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                argv = [str(item).strip() for item in parsed if str(item).strip()]
                if argv:
                    return self._resolve_start_command(argv)
        return self._resolve_start_command(shlex.split(raw, posix=os.name != "nt"))

    def _resolve_start_command(self, argv: list[str]) -> list[str]:
        if not argv:
            return []

        executable = str(argv[0]).strip()
        if not executable:
            return []
        if Path(executable).exists():
            return self._wrap_windows_launcher(argv)

        resolved = shutil.which(executable)
        if resolved:
            updated = list(argv)
            updated[0] = resolved
            return self._wrap_windows_launcher(updated)

        if os.name == "nt" and executable.lower() == "openclaw":
            appdata = Path(os.getenv("APPDATA", "")).expanduser()
            cmd_candidate = appdata / "npm" / "openclaw.cmd"
            if cmd_candidate.exists():
                updated = list(argv)
                updated[0] = str(cmd_candidate)
                return self._wrap_windows_launcher(updated)
            ps1_candidate = appdata / "npm" / "openclaw.ps1"
            if ps1_candidate.exists():
                return self._wrap_windows_launcher([str(ps1_candidate), *argv[1:]])

        return argv

    def _wrap_windows_launcher(self, argv: list[str]) -> list[str]:
        if os.name != "nt" or not argv:
            return argv

        executable = str(argv[0]).strip().lower()
        if executable.endswith((".cmd", ".bat")):
            return [
                os.getenv("COMSPEC", "cmd.exe"),
                "/c",
                argv[0],
                *argv[1:],
            ]
        if executable.endswith(".ps1"):
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                argv[0],
                *argv[1:],
            ]
        return argv

    def ensure_gateway_running(self) -> tuple[bool, str | None]:
        if self._gateway_is_healthy():
            return True, None
        if not self.config.auto_start:
            return False, f"gateway unreachable and auto-start disabled at {self.config.health_url}"

        with self._start_lock:
            if self._gateway_is_healthy():
                return True, None

            argv = self._start_command_argv()
            if not argv:
                return False, "gateway unreachable and no OpenClaw start command is configured"

            popen_kwargs: dict[str, Any] = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            else:
                popen_kwargs["start_new_session"] = True

            try:
                subprocess.Popen(argv, **popen_kwargs)
            except Exception as exc:
                return False, f"gateway unreachable and auto-start failed: {exc}"

            deadline = time.monotonic() + (self.config.auto_start_timeout_ms / 1000.0)
            while time.monotonic() < deadline:
                if self._gateway_is_healthy():
                    return True, None
                time.sleep(0.5)

        return False, f"gateway unreachable and auto-start did not become healthy within {self.config.auto_start_timeout_ms} ms"

    def forward_prompt(
        self,
        text: str,
        *,
        prompt_id: str,
        metadata: dict[str, Any] | None = None,
        on_accept: Callable[[str | None], None] | None = None,
        session_key: str | None = None,
    ) -> OpenClawBridgeResult:
        if not self.config.enabled:
            return OpenClawBridgeResult(ok=False, attempted=False, accepted=False, error="direct bridge disabled")

        gateway_ok, gateway_error = self.ensure_gateway_running()
        if not gateway_ok:
            return OpenClawBridgeResult(ok=False, attempted=False, accepted=False, error=gateway_error)

        payload = {
            "model": self.config.model,
            "input": text,
            "stream": True,
            "user": self.config.user,
            "metadata": {
                "source": "asteria",
                "prompt_id": prompt_id,
                **(metadata or {}),
            },
        }
        data = json.dumps(payload).encode("utf-8")
        resolved_session_key = str(session_key or self.session_key_for_prompt(prompt_id)).strip() or self.config.session_key
        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
            "User-Agent": "asteria-openclaw-bridge/1",
            self.config.session_header: resolved_session_key,
        }
        if self.config.gateway_token:
            headers["Authorization"] = f"Bearer {self.config.gateway_token}"

        request = urllib.request.Request(
            url=self.config.endpoint_url,
            data=data,
            method="POST",
            headers=headers,
        )

        try:
            response = urllib.request.urlopen(request, timeout=self.config.timeout_ms / 1000.0)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return OpenClawBridgeResult(
                ok=False,
                attempted=True,
                accepted=False,
                status_code=exc.code,
                error=f"gateway HTTP {exc.code}: {_short_body(body) or exc.reason}",
                response_body=_short_body(body),
            )
        except urllib.error.URLError as exc:
            return OpenClawBridgeResult(
                ok=False,
                attempted=True,
                accepted=False,
                error=f"gateway unreachable: {exc.reason}",
            )
        except Exception as exc:
            return OpenClawBridgeResult(
                ok=False,
                attempted=True,
                accepted=False,
                error=f"bridge send failed: {exc}",
            )

        status_code = int(getattr(response, "status", 200))
        accepted = False
        response_id: str | None = None
        response_body = ""
        final_ok = True
        final_error: str | None = None
        current_event: str | None = None
        current_data: list[str] = []
        saw_done = False

        def finalize_event() -> None:
            nonlocal accepted, response_id, response_body, final_ok, final_error, current_event, current_data, saw_done
            if not current_event and not current_data:
                current_event = None
                current_data = []
                return

            payload_text = "\n".join(current_data).strip()
            if payload_text == "[DONE]":
                saw_done = True
                current_event = None
                current_data = []
                return
            response_body = payload_text or response_body
            parsed: Any = None
            if payload_text:
                try:
                    parsed = json.loads(payload_text)
                except json.JSONDecodeError:
                    parsed = None

            if parsed is not None and response_id is None:
                response_id = _response_id_from_payload(parsed)

            if not accepted and current_event in {"response.created", "response.in_progress"}:
                accepted = True
                if on_accept is not None:
                    on_accept(response_id)

            if current_event == "response.failed":
                final_ok = False
                final_error = _response_error_from_payload(parsed) or "OpenClaw reported a failed response"

            status = _response_status_from_payload(parsed)
            if current_event == "response.completed" or status == "completed":
                final_ok = True
            elif status == "failed":
                final_ok = False
                final_error = _response_error_from_payload(parsed) or "OpenClaw reported a failed response"

            current_event = None
            current_data = []

        try:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    finalize_event()
                    if saw_done:
                        break
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    current_event = line[6:].strip() or None
                    continue
                if line.startswith("data:"):
                    current_data.append(line[5:].lstrip())
                    continue
            finalize_event()
        except urllib.error.URLError as exc:
            if not accepted:
                return OpenClawBridgeResult(
                    ok=False,
                    attempted=True,
                    accepted=False,
                    status_code=status_code,
                    error=f"gateway stream failed before acceptance: {exc.reason}",
                )
            final_ok = True
            final_error = None
        except Exception as exc:
            if not accepted:
                return OpenClawBridgeResult(
                    ok=False,
                    attempted=True,
                    accepted=False,
                    status_code=status_code,
                    error=f"bridge send failed: {exc}",
                )
            final_ok = True
            final_error = None
        finally:
            try:
                response.close()
            except Exception:
                pass

        if not accepted:
            return OpenClawBridgeResult(
                ok=False,
                attempted=True,
                accepted=False,
                status_code=status_code,
                error=f"gateway returned no acceptance event at {self.config.endpoint_url}",
                response_body=_short_body(response_body),
            )

        return OpenClawBridgeResult(
            ok=final_ok,
            attempted=True,
            accepted=True,
            status_code=status_code,
            response_id=response_id,
            error=final_error,
            response_body=_short_body(response_body),
        )
