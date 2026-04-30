from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass(slots=True)
class MobileImageSummary:
    url: str | None = None
    path: str | None = None
    captured_at: str | None = None
    width: int | None = None
    height: int | None = None


@dataclass(slots=True)
class TeleopVector:
    forward: float = 0.0
    turn: float = 0.0
    strafe: float = 0.0
    ttl_ms: int = 300
    source: str = "3ds"

    def clamped(self) -> "TeleopVector":
        return TeleopVector(
            forward=max(-1.0, min(1.0, float(self.forward))),
            turn=max(-1.0, min(1.0, float(self.turn))),
            strafe=max(-1.0, min(1.0, float(self.strafe))),
            ttl_ms=max(100, min(2000, int(self.ttl_ms))),
            source=self.source,
        )


@dataclass(slots=True)
class TeleopState:
    active: bool = False
    holder_id: str | None = None
    holder_label: str | None = None
    vector: TeleopVector = field(default_factory=TeleopVector)
    expires_at: str | None = None
    blocked_reason: str | None = None


@dataclass(slots=True)
class AgentTurn:
    id: str
    role: str
    content: str
    created_at: str = field(default_factory=utc_now_iso)
    kind: str = "message"
    blocked_action: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentJob:
    id: str
    session_id: str
    state: str = "queued"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    error: str | None = None


@dataclass(slots=True)
class AgentSessionSummary:
    id: str
    title: str
    state: str = "idle"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_message_preview: str | None = None
    unread_count: int = 0


@dataclass(slots=True)
class MobileAuthConfig:
    device_token: str
    device_name: str = "Asteria DS"
    holder_id: str = "asteria-ds"
    holder_label: str = "Asteria DS"
    created_at: str = field(default_factory=utc_now_iso)
    enabled: bool = True


@dataclass(slots=True)
class MobileStatus:
    connected: bool
    runtime_mode: str
    manual_control_allowed: bool
    lease_holder: str | None
    lease_holder_id: str | None = None
    lease_holder_kind: str | None = None
    lease_active: bool = False
    lease_seconds_remaining: int = 0
    battery_percent: int | None = None
    robot_host: str | None = None
    pose: dict[str, Any] = field(default_factory=dict)
    active_fsm: str | None = None
    latest_image: MobileImageSummary = field(default_factory=MobileImageSummary)
    latest_image_preview_url: str | None = None
    active_session: AgentSessionSummary | None = None
    teleop: TeleopState = field(default_factory=TeleopState)
    last_action: str | None = None
    last_result: str | None = None
    supports_fsm_runtime: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
