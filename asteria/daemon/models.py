from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ControlLease:
    holder_id: str = ""
    holder_label: str = "Unclaimed"
    holder_kind: str = "available"
    priority: int = 0
    expires_at_epoch: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TelemetrySnapshot:
    connected: bool = False
    host: str | None = None
    running_fsm_name: str | None = None
    running_fsm_active: bool = False
    battery_pct: float | None = None
    pose: dict[str, Any] = field(default_factory=dict)
    last_error: str = ""
    runtime_error: str = ""
    last_image_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivityEntry:
    id: str
    timestamp: str
    actor_id: str
    actor_label: str
    actor_kind: str
    kind: str
    title: str
    detail: str = ""
    status: str = "info"
    related_action: str | None = None
    prompt_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PromptEntry:
    id: str
    submitted_at: str
    submitted_by: str
    submitted_label: str
    text: str
    forward_mode: str = "queue"
    status: str = "pending"
    forward_status: str = "not_sent"
    forwarded_at: str | None = None
    forward_error: str | None = None
    forward_attempts: int = 0
    bridge_session_key: str | None = None
    response: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None
    resolved_label: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
