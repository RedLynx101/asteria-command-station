from __future__ import annotations

from typing import Any


class MockRuntimeAdapter:
    """Tiny adapter to exercise MobileBridgeService locally."""

    def __init__(self) -> None:
        self._lease_holder = None
        self._last_action = "idle"
        self._latest_image = {
            "url": "",
            "captured_at": "",
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": True,
            "runtime_mode": "agent_direct",
            "manual_control_allowed": True,
            "lease_holder": self._lease_holder,
            "battery_percent": 82,
            "robot_host": "127.0.0.1",
            "pose": {"x_mm": 100, "y_mm": -40, "heading_deg": 88},
            "active_fsm": "InspectBarrel",
            "last_action": self._last_action,
            "last_result": "ok",
            "supports_fsm_runtime": True,
            "latest_image": self._latest_image,
        }

    def claim_lease(self, holder_id: str, holder_label: str, takeover: bool = False) -> dict[str, Any]:
        if self._lease_holder and self._lease_holder != holder_label and not takeover:
            return {"granted": False, "blocked_reason": "Lease already held by another human"}
        self._lease_holder = holder_label
        self._last_action = "claim_lease"
        return {"granted": True}

    def release_lease(self, holder_id: str) -> dict[str, Any]:
        self._lease_holder = None
        self._last_action = "release_lease"
        return {"released": True}

    def send_direct_command(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._last_action = command
        return {"ok": True, "command": command, "payload": payload}

    def capture_image(self) -> dict[str, Any]:
        self._latest_image = {"url": "mock://latest-image", "captured_at": "now"}
        self._last_action = "capture_image"
        return {"ok": True, **self._latest_image}

    def latest_image(self) -> dict[str, Any] | None:
        return self._latest_image
