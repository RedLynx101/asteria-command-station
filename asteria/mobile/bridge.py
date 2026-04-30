from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .auth import constant_time_match
from .preview import ensure_rgb565_preview
from .session_store import AgentSessionStore
from .types import (
    AgentJob,
    AgentSessionSummary,
    MobileImageSummary,
    MobileStatus,
    TeleopState,
    TeleopVector,
    utc_now_iso,
)


class MobileBridgeService:
    """Framework-agnostic service layer for Asteria DS mobile endpoints.

    Integrate this with the repo's existing daemon runtime by passing a runtime_adapter
    object that exposes a small surface:

    - get_status() -> dict
    - claim_lease(holder_id, holder_label, takeover=False) -> dict
    - release_lease(holder_id) -> dict
    - send_direct_command(command: str, payload: dict) -> dict
    - capture_image() -> dict
    - latest_image() -> dict | None
    - submit_prompt(text: str, holder_id: str, holder_label: str) -> dict
    """

    def __init__(self, runtime_adapter: Any, auth_token: str, artifacts_root: str | Path):
        self.runtime_adapter = runtime_adapter
        self.auth_token = auth_token
        self.artifacts_root = Path(artifacts_root)
        self.store = AgentSessionStore(self.artifacts_root / "mobile-sessions")
        self.teleop_state = TeleopState()
        self.preview_root = self.artifacts_root / "mobile-previews"
        self.preview_script = self.artifacts_root.parent.parent / "scripts" / "asteria_make_mobile_preview.ps1"

    def check_auth(self, provided_token: str) -> None:
        if not constant_time_match(self.auth_token, provided_token or ""):
            raise PermissionError("Invalid mobile bearer token")

    def bootstrap(self) -> dict[str, Any]:
        status = self.status()
        sessions = [asdict(item) for item in self.store.list_sessions()[:8]]
        return {
            "status": status,
            "sessions": sessions,
            "server_time": utc_now_iso(),
        }

    def status(self) -> dict[str, Any]:
        base = self.runtime_adapter.get_status()
        latest_image_dict = base.get("latest_image") or self.runtime_adapter.latest_image() or {}
        sessions = self.store.list_sessions()
        active_session = sessions[0] if sessions else None

        payload = MobileStatus(
            connected=bool(base.get("connected")),
            runtime_mode=base.get("runtime_mode", "idle"),
            manual_control_allowed=bool(base.get("manual_control_allowed", True)),
            lease_holder=base.get("lease_holder"),
            lease_holder_id=base.get("lease_holder_id"),
            lease_holder_kind=base.get("lease_holder_kind"),
            lease_active=bool(base.get("lease_active", False)),
            lease_seconds_remaining=int(base.get("lease_seconds_remaining", 0) or 0),
            battery_percent=base.get("battery_percent"),
            robot_host=base.get("robot_host"),
            pose=base.get("pose") or {},
            active_fsm=base.get("active_fsm"),
            latest_image=MobileImageSummary(**latest_image_dict),
            latest_image_preview_url=base.get("latest_image_preview_url"),
            active_session=active_session,
            teleop=self.teleop_state,
            last_action=base.get("last_action"),
            last_result=base.get("last_result"),
            supports_fsm_runtime=bool(base.get("supports_fsm_runtime", False)),
        )
        return payload.to_dict()

    def _teleop_payload(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = dict(payload or {})
        if self.teleop_state.holder_id:
            merged.setdefault("holder_id", self.teleop_state.holder_id)
        if self.teleop_state.holder_label:
            merged.setdefault("holder_label", self.teleop_state.holder_label)
        merged.setdefault("holder_kind", "human")
        return merged

    def list_sessions(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self.store.list_sessions()]

    def create_session(self, title: str) -> dict[str, Any]:
        session = self.store.create_session(title=title or "New Chat")
        return asdict(session)

    def get_session(self, session_id: str) -> dict[str, Any]:
        summary = self.store.get_session(session_id)
        turns = [asdict(turn) for turn in self.store.read_turns(session_id)]
        job = asdict(self.store.get_job(session_id))
        return {"summary": asdict(summary), "turns": turns, "job": job}

    def add_message(self, session_id: str, content: str) -> dict[str, Any]:
        if not content.strip():
            raise ValueError("Message content is required")

        self.store.append_turn(session_id, "user", content)
        session = self.store.get_session(session_id)
        session.state = "queued"
        self.store.update_session(session)

        job = self.store.get_job(session_id)
        job.state = "queued"
        self.store.update_job(session_id, job)

        return self.get_session(session_id)

    def append_agent_reply(self, session_id: str, content: str, *, blocked_action: bool = False, **metadata) -> dict[str, Any]:
        turn = self.store.append_turn(session_id, "assistant", content, blocked_action=blocked_action, **metadata)
        session = self.store.get_session(session_id)
        session.state = "idle"
        self.store.update_session(session)
        job = self.store.get_job(session_id)
        job.state = "idle"
        self.store.update_job(session_id, job)
        return asdict(turn)

    def cancel_session_job(self, session_id: str) -> dict[str, Any]:
        job = self.store.cancel_job(session_id)
        return asdict(job)

    def claim_teleop(self, holder_id: str, holder_label: str, takeover: bool = False) -> dict[str, Any]:
        result = self.runtime_adapter.claim_lease(holder_id=holder_id, holder_label=holder_label, takeover=takeover)
        self.teleop_state.active = bool(result.get("granted"))
        self.teleop_state.holder_id = holder_id if self.teleop_state.active else None
        self.teleop_state.holder_label = holder_label if self.teleop_state.active else None
        self.teleop_state.blocked_reason = result.get("blocked_reason")
        return {"teleop": asdict(self.teleop_state), "lease": result}

    def release_teleop(self, holder_id: str) -> dict[str, Any]:
        result = self.runtime_adapter.release_lease(holder_id=holder_id)
        self.teleop_state = TeleopState()
        return {"teleop": asdict(self.teleop_state), "lease": result}

    def teleop_vector(self, vector: dict[str, Any]) -> dict[str, Any]:
        normalized = TeleopVector(**vector).clamped()
        self.teleop_state.active = True
        self.teleop_state.vector = normalized
        self.teleop_state.expires_at = utc_now_iso()
        lane_result = self.runtime_adapter.send_direct_command("teleop_vector", self._teleop_payload(asdict(normalized)))
        return {"teleop": asdict(self.teleop_state), "result": lane_result}

    def teleop_stop(self) -> dict[str, Any]:
        self.teleop_state.vector = TeleopVector()
        self.teleop_state.active = False
        result = self.runtime_adapter.send_direct_command("stop_all", self._teleop_payload({"stop_fsm": False}))
        return {"teleop": asdict(self.teleop_state), "result": result}

    def teleop_command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.runtime_adapter.send_direct_command(command, self._teleop_payload(payload))
        return {"result": result}

    def capture_image(self) -> dict[str, Any]:
        return self.runtime_adapter.send_direct_command("capture_image", self._teleop_payload())

    def submit_prompt(self, text: str, *, holder_id: str, holder_label: str) -> dict[str, Any]:
        return self.runtime_adapter.submit_prompt(text=text, holder_id=holder_id, holder_label=holder_label)

    def latest_image(self) -> dict[str, Any]:
        return self.runtime_adapter.latest_image() or {}

    def latest_image_preview_rgb565(self, *, width: int = 176, height: int = 132) -> bytes:
        latest = self.runtime_adapter.latest_image() or {}
        image_path = latest.get("path")
        if not image_path:
            raise FileNotFoundError("no captured image is available")
        return ensure_rgb565_preview(
            Path(image_path),
            self.preview_root,
            self.preview_script,
            width=width,
            height=height,
        )
