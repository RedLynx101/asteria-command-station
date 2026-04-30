from __future__ import annotations

import time
from typing import Any

from asteria.daemon.runtime import AsteriaRuntime


class AsteriaMobileRuntimeAdapter:
    """Thin adapter that exposes the current daemon runtime to mobile clients."""

    def __init__(
        self,
        runtime: AsteriaRuntime,
        *,
        holder_id: str = "asteria-ds",
        holder_label: str = "Asteria DS",
        holder_kind: str = "human",
    ) -> None:
        self.runtime = runtime
        self.default_holder = {
            "holder_id": holder_id,
            "holder_label": holder_label,
            "holder_kind": holder_kind,
        }
        self._last_vector_dispatch_at = 0.0

    def _holder_payload(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = dict(self.default_holder)
        if payload:
            merged.update({key: value for key, value in payload.items() if value is not None})
        return merged

    def _unsupported(self, command: str, message: str) -> dict[str, Any]:
        status = self.runtime.status()
        return {
            "ok": False,
            "error": f"{command} is unsupported on the current Asteria runtime: {message}",
            **status,
        }

    def get_status(self) -> dict[str, Any]:
        status = self.runtime.status()
        telemetry = status.get("telemetry", {})
        connection = status.get("connection", {})
        lease = status.get("lease", {})
        pose = telemetry.get("pose") or {}
        last_result = status.get("last_result") or {}
        lease_expires_at = float(lease.get("expires_at_epoch") or 0.0)
        lease_seconds_remaining = max(0, int(round(lease_expires_at - time.time())))
        latest_image = status.get("latest_image") or self.latest_image() or {}
        return {
            "connected": bool(telemetry.get("connected")),
            "runtime_mode": connection.get("connected_runtime_mode") or "idle",
            "manual_control_allowed": not lease.get("holder_id") or lease.get("holder_id") == self.default_holder["holder_id"],
            "lease_holder": lease.get("holder_label") if lease.get("holder_id") else None,
            "lease_holder_id": lease.get("holder_id") if lease.get("holder_id") else None,
            "lease_holder_kind": lease.get("holder_kind") if lease.get("holder_id") else None,
            "lease_active": bool(lease.get("holder_id")) and lease_seconds_remaining > 0,
            "lease_seconds_remaining": lease_seconds_remaining,
            "battery_percent": round(telemetry["battery_pct"]) if telemetry.get("battery_pct") is not None else None,
            "robot_host": telemetry.get("host") or connection.get("resolved_host"),
            "pose": {
                "x_mm": round(pose.get("x", 0)) if pose.get("x") is not None else None,
                "y_mm": round(pose.get("y", 0)) if pose.get("y") is not None else None,
                "heading_deg": round(pose.get("heading", 0)) if pose.get("heading") is not None else None,
            },
            "active_fsm": telemetry.get("running_fsm_name"),
            "last_action": status.get("last_action"),
            "last_result": last_result.get("error") or last_result.get("message"),
            "supports_fsm_runtime": bool(connection.get("supports_fsm_runtime")),
            "latest_image": latest_image,
            "latest_image_preview_url": "/api/mobile/images/preview?width=176&height=132" if latest_image.get("url") else None,
        }

    def claim_lease(self, holder_id: str, holder_label: str, takeover: bool = False) -> dict[str, Any]:
        result = self.runtime.dispatch("lease_claim", {
            "holder_id": holder_id,
            "holder_label": holder_label,
            "holder_kind": "human",
            "force": takeover,
        })
        return {
            "granted": bool(result.get("ok")),
            "blocked_reason": result.get("error"),
            "lease": result.get("lease"),
            "status": result,
        }

    def release_lease(self, holder_id: str) -> dict[str, Any]:
        result = self.runtime.dispatch("lease_release", {"holder_id": holder_id})
        return {
            "released": bool(result.get("ok")),
            "blocked_reason": result.get("error"),
            "lease": result.get("lease"),
            "status": result,
        }

    def _vector_to_command(self, payload: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        now = time.time()
        if now - self._last_vector_dispatch_at < 0.08:
            return None

        forward = float(payload.get("forward", 0.0))
        turn = float(payload.get("turn", 0.0))
        strafe = float(payload.get("strafe", 0.0))
        dominant = max(
            (abs(forward), "forward"),
            (abs(turn), "turn"),
            (abs(strafe), "strafe"),
        )

        magnitude, axis = dominant
        if magnitude < 0.18:
            return None

        self._last_vector_dispatch_at = now
        if axis == "forward":
            return "drive_at", {
                "angle_deg": 0.0 if forward >= 0 else 180.0,
                "speed_pct": round(20 + magnitude * 55),
            }
        if axis == "strafe":
            return "drive_at", {
                "angle_deg": 90.0 if strafe >= 0 else -90.0,
                "speed_pct": round(20 + magnitude * 55),
            }
        return "turn_at", {"turn_rate_pct": round((18 + magnitude * 42) * (1 if turn >= 0 else -1))}

    def send_direct_command(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        full_payload = self._holder_payload(payload)

        if command == "teleop_vector":
            mapped = self._vector_to_command(full_payload)
            if mapped is None:
                return {"ok": True, "message": "teleop vector below deadzone or rate-limited", **self.runtime.status()}
            mapped_command, mapped_payload = mapped
            full_payload = self._holder_payload({**full_payload, **mapped_payload})
            return self.runtime.dispatch(mapped_command, full_payload)

        if command in {"connect", "disconnect", "reconnect"}:
            return self.runtime.dispatch(command, full_payload)

        if command == "grab_assist":
            pickup_payload = dict(full_payload)
            pickup_payload["style"] = "soft"
            result = self.runtime.dispatch("kick", pickup_payload)
            if result.get("ok"):
                result["message"] = "pickup fallback issued as soft kick"
            return result

        if command == "place":
            return self._unsupported(command, "place is not available as a direct bridge action yet")

        if command not in {"stop_all", "move", "sideways", "turn", "drive_at", "turn_at", "kick", "say", "capture_image"}:
            return self._unsupported(command, "unknown mobile command")

        return self.runtime.dispatch(command, full_payload)

    def capture_image(self) -> dict[str, Any]:
        return self.send_direct_command("capture_image", {})

    def latest_image(self) -> dict[str, Any] | None:
        summary = self.runtime.latest_image_summary()
        return summary or None

    def submit_prompt(self, text: str, holder_id: str | None = None, holder_label: str | None = None) -> dict[str, Any]:
        payload = self._holder_payload({
            "holder_id": holder_id or self.default_holder["holder_id"],
            "holder_label": holder_label or self.default_holder["holder_label"],
            "holder_kind": "human",
            "text": text,
        })
        return self.runtime.dispatch("submit_prompt", payload)
