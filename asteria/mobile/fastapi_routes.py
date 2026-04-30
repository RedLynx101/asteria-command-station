from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from .bridge import MobileBridgeService


def build_mobile_router(service: MobileBridgeService) -> APIRouter:
    router = APIRouter(prefix="/api/mobile", tags=["mobile"])

    def guard(authorization: str | None) -> None:
        token = (authorization or "").removeprefix("Bearer ").strip()
        try:
            service.check_auth(token)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @router.get("/bootstrap")
    def bootstrap(authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.bootstrap()

    @router.get("/status")
    def status(authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.status()

    @router.get("/chat/sessions")
    def list_sessions(authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.list_sessions()

    @router.post("/chat/sessions")
    def create_session(payload: dict, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.create_session(title=payload.get("title", "New Chat"))

    @router.get("/chat/sessions/{session_id}")
    def get_session(session_id: str, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.get_session(session_id)

    @router.post("/chat/sessions/{session_id}/messages")
    def add_message(session_id: str, payload: dict, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.add_message(session_id, payload.get("content", ""))

    @router.post("/chat/sessions/{session_id}/cancel")
    def cancel_session(session_id: str, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.cancel_session_job(session_id)

    @router.post("/teleop/claim")
    def claim(payload: dict, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.claim_teleop(
            holder_id=payload.get("holder_id", "asteria-ds"),
            holder_label=payload.get("holder_label", "Asteria DS"),
            takeover=bool(payload.get("takeover", False)),
        )

    @router.post("/teleop/release")
    def release(payload: dict, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.release_teleop(holder_id=payload.get("holder_id", "asteria-ds"))

    @router.post("/teleop/vector")
    def teleop_vector(payload: dict, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.teleop_vector(payload)

    @router.post("/teleop/stop")
    def teleop_stop(authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.teleop_stop()

    @router.post("/teleop/command")
    def teleop_command(payload: dict, authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.teleop_command(command=payload.get("command", ""), payload=payload)

    @router.get("/images/latest")
    def latest_image(authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.latest_image()

    @router.post("/images/capture")
    def capture_image(authorization: str | None = Header(default=None)):
        guard(authorization)
        return service.capture_image()

    return router
