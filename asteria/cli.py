from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8766"


def request_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 30,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Asteria HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Asteria unreachable at {url}: {exc.reason}") from exc

    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Asteria returned non-JSON payload: {body}") from exc


def send_action(base_url: str, action: str, holder_id: str, holder_label: str, holder_kind: str, **payload: Any) -> dict[str, Any]:
    return request_json(
        f"{base_url.rstrip('/')}/api/command",
        method="POST",
        payload={
            "action": action,
            "holder_id": holder_id,
            "holder_label": holder_label,
            "holder_kind": holder_kind,
            **payload,
        },
        timeout=180,
    )


def get_status(base_url: str) -> dict[str, Any]:
    return request_json(f"{base_url.rstrip('/')}/api/status")


def claim_lease(base_url: str, holder_id: str, holder_label: str, holder_kind: str, force: bool) -> dict[str, Any]:
    return request_json(
        f"{base_url.rstrip('/')}/api/lease/claim",
        method="POST",
        payload={
            "holder_id": holder_id,
            "holder_label": holder_label,
            "holder_kind": holder_kind,
            "force": force,
        },
    )


def release_lease(base_url: str, holder_id: str) -> dict[str, Any]:
    return request_json(
        f"{base_url.rstrip('/')}/api/lease/release",
        method="POST",
        payload={"holder_id": holder_id},
    )


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI client for the local Asteria daemon.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Asteria base URL.")
    parser.add_argument("--holder-id", default="openclaw", help="Controller identifier for lease-gated commands.")
    parser.add_argument("--holder-label", default="OpenClaw", help="Controller display label.")
    parser.add_argument("--holder-kind", default="agent", choices=("agent", "human"), help="Controller kind.")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status", help="Read daemon status.")

    claim = sub.add_parser("claim-lease", help="Claim the control lease.")
    claim.add_argument("--force", action="store_true", help="Force preemption if allowed.")

    sub.add_parser("release-lease", help="Release the control lease.")
    connect = sub.add_parser("connect", help="Connect to the robot (auto full AIM first, then minimal fallback).")
    connect.add_argument("--host", "--target", dest="host", help="Explicit robot target for this connect attempt.")
    sub.add_parser("disconnect", help="Disconnect from the robot.")
    reconnect = sub.add_parser("reconnect", help="Reconnect to the robot (auto full AIM first, then minimal fallback).")
    reconnect.add_argument("--host", "--target", dest="host", help="Explicit robot target for this reconnect attempt.")
    stop_all = sub.add_parser("stop-all", help="Emergency stop.")
    stop_policy = stop_all.add_mutually_exclusive_group()
    stop_policy.add_argument("--stop-fsm", dest="stop_fsm", action="store_true", help="Also unload the active FSM while stopping.")
    stop_policy.add_argument("--keep-fsm", dest="stop_fsm", action="store_false", help="Stop motion only and leave the active FSM loaded.")
    stop_all.set_defaults(stop_fsm=True)
    sub.add_parser("capture-image", help="Capture an image.")

    set_connection = sub.add_parser("set-connection", help="Update daemon-side connection targeting.")
    set_connection.add_argument("--profile", help="Target profile name such as home or cmu.")
    set_connection.add_argument("--host", "--target", dest="robot_target", help="Robot target, hostname, IP, or short AIM id.")
    set_connection.add_argument("--robot-id", dest="robot_target", help="Short AIM id such as AIM-526BA018.")
    set_connection.add_argument("--fallback-hosts", help="Comma-separated fallback host list.")
    set_connection.add_argument("--clear-override", action="store_true", help="Clear the current host override.")
    set_connection.add_argument("--reset-fallbacks", action="store_true", help="Clear manual fallback overrides.")

    save_profile = sub.add_parser("save-profile-target", help="Persist a robot target into the selected profile env file.")
    save_profile.add_argument("--profile", required=True, help="Profile name such as home or cmu.")
    save_profile.add_argument("--host", "--target", dest="robot_target", help="Robot target, hostname, IP, or short AIM id.")
    save_profile.add_argument("--robot-id", dest="robot_target", help="Short AIM id such as AIM-526BA018.")

    diagnose_connection = sub.add_parser("diagnose-connection", help="Resolve and inspect current connection targets.")
    diagnose_connection.add_argument("--host", help="Optional explicit host to include first.")

    submit_prompt = sub.add_parser("submit-prompt", help="Submit a shared prompt/request into the Asteria desk.")
    submit_prompt.add_argument("--text", required=True)

    list_prompts = sub.add_parser("list-prompts", help="List shared-desk prompts.")
    list_scope = list_prompts.add_mutually_exclusive_group()
    list_scope.add_argument("--pending-only", dest="pending_only", action="store_true", help="Show unresolved prompts only.")
    list_scope.add_argument("--all", dest="pending_only", action="store_false", help="Show recent prompts regardless of status.")
    list_prompts.set_defaults(pending_only=True)
    list_prompts.add_argument("--limit", type=int, default=10)

    log_note = sub.add_parser("log-note", help="Post a human or agent note into the Asteria activity feed.")
    log_note.add_argument("--message", required=True)
    log_note.add_argument("--title", help="Optional short title.")
    log_note.add_argument("--level", default="info", choices=("info", "ok", "warn", "error"))

    resolve_prompt = sub.add_parser("resolve-prompt", help="Mark a shared prompt as resolved.")
    resolve_prompt.add_argument("--prompt-id", required=True)
    resolve_prompt.add_argument("--response", help="Optional response text.")

    retry_prompt_forward = sub.add_parser("retry-prompt-forward", help="Retry direct OpenClaw forwarding for a shared prompt.")
    retry_prompt_forward.add_argument("--prompt-id", required=True)

    move = sub.add_parser("move", help="Move by distance/angle.")
    move.add_argument("--distance-mm", type=float, required=True)
    move.add_argument("--angle-deg", type=float, default=0.0)

    sideways = sub.add_parser("sideways", help="Strafe sideways.")
    sideways.add_argument("--distance-mm", type=float, required=True)

    turn = sub.add_parser("turn", help="Turn in place.")
    turn.add_argument("--angle-deg", type=float, required=True)

    say = sub.add_parser("say", help="Display text on the robot.")
    say.add_argument("--text", required=True)

    kick = sub.add_parser("kick", help="Trigger the kicker.")
    kick.add_argument("--style", default="medium", choices=("soft", "medium", "hard"))

    create_fsm = sub.add_parser("create-fsm", help="Create or overwrite an FSM source file.")
    create_fsm.add_argument("--name", required=True)
    create_fsm.add_argument("--content", help="Optional FSM source content.")

    compile_fsm = sub.add_parser("compile-fsm", help="Compile an FSM source file.")
    compile_fsm.add_argument("--name")
    compile_fsm.add_argument("--fsm-path")

    run_fsm = sub.add_parser("run-fsm", help="Run a compiled FSM module.")
    run_fsm.add_argument("--module", required=True)

    sub.add_parser("unload-fsm", help="Unload the active FSM and stop robot motion.")

    send_text = sub.add_parser("send-text", help="Send a text event to the active FSM.")
    send_text.add_argument("--message", required=True)

    send_speech = sub.add_parser("send-speech", help="Send a speech event to the active FSM.")
    send_speech.add_argument("--message", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.action == "status":
            result = get_status(args.base_url)
        elif args.action == "claim-lease":
            result = claim_lease(args.base_url, args.holder_id, args.holder_label, args.holder_kind, args.force)
        elif args.action == "release-lease":
            result = release_lease(args.base_url, args.holder_id)
        elif args.action == "connect":
            payload: dict[str, Any] = {}
            if args.host:
                payload["host"] = args.host
            result = send_action(args.base_url, "connect", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "disconnect":
            result = send_action(args.base_url, "disconnect", args.holder_id, args.holder_label, args.holder_kind)
        elif args.action == "reconnect":
            payload = {}
            if args.host:
                payload["host"] = args.host
            result = send_action(args.base_url, "reconnect", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "set-connection":
            payload = {}
            if args.profile:
                payload["profile"] = args.profile
            if args.robot_target is not None:
                payload["robot_target"] = args.robot_target
            if args.fallback_hosts is not None:
                payload["fallback_hosts"] = args.fallback_hosts
            if args.clear_override:
                payload["clear_override"] = True
            if args.reset_fallbacks:
                payload["reset_fallbacks"] = True
            result = send_action(args.base_url, "set_connection_config", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "diagnose-connection":
            payload = {}
            if args.host:
                payload["host"] = args.host
            result = send_action(args.base_url, "diagnose_connection", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "submit-prompt":
            result = send_action(args.base_url, "submit_prompt", args.holder_id, args.holder_label, args.holder_kind, text=args.text)
        elif args.action == "list-prompts":
            result = send_action(
                args.base_url,
                "list_prompts",
                args.holder_id,
                args.holder_label,
                args.holder_kind,
                pending_only=args.pending_only,
                limit=args.limit,
            )
        elif args.action == "log-note":
            payload = {"message": args.message, "level": args.level}
            if args.title:
                payload["title"] = args.title
            result = send_action(args.base_url, "log_note", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "resolve-prompt":
            payload = {"prompt_id": args.prompt_id}
            if args.response:
                payload["response"] = args.response
            result = send_action(args.base_url, "resolve_prompt", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "retry-prompt-forward":
            result = send_action(
                args.base_url,
                "retry_prompt_forward",
                args.holder_id,
                args.holder_label,
                args.holder_kind,
                prompt_id=args.prompt_id,
            )
        elif args.action == "save-profile-target":
            payload = {"profile": args.profile}
            if args.robot_target:
                payload["robot_target"] = args.robot_target
            result = send_action(args.base_url, "save_profile_robot_target", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "stop-all":
            result = send_action(args.base_url, "stop_all", args.holder_id, args.holder_label, args.holder_kind, stop_fsm=args.stop_fsm)
        elif args.action == "capture-image":
            result = send_action(args.base_url, "capture_image", args.holder_id, args.holder_label, args.holder_kind)
        elif args.action == "move":
            result = send_action(args.base_url, "move", args.holder_id, args.holder_label, args.holder_kind, distance_mm=args.distance_mm, angle_deg=args.angle_deg)
        elif args.action == "sideways":
            result = send_action(args.base_url, "sideways", args.holder_id, args.holder_label, args.holder_kind, distance_mm=args.distance_mm)
        elif args.action == "turn":
            result = send_action(args.base_url, "turn", args.holder_id, args.holder_label, args.holder_kind, angle_deg=args.angle_deg)
        elif args.action == "say":
            result = send_action(args.base_url, "say", args.holder_id, args.holder_label, args.holder_kind, text=args.text)
        elif args.action == "kick":
            result = send_action(args.base_url, "kick", args.holder_id, args.holder_label, args.holder_kind, style=args.style)
        elif args.action == "create-fsm":
            result = send_action(args.base_url, "create_fsm", args.holder_id, args.holder_label, args.holder_kind, name=args.name, content=args.content)
        elif args.action == "compile-fsm":
            payload: dict[str, Any] = {}
            if args.name:
                payload["name"] = args.name
            if args.fsm_path:
                payload["fsm_path"] = args.fsm_path
            result = send_action(args.base_url, "compile_fsm", args.holder_id, args.holder_label, args.holder_kind, **payload)
        elif args.action == "run-fsm":
            result = send_action(args.base_url, "run_fsm", args.holder_id, args.holder_label, args.holder_kind, module=args.module)
        elif args.action == "unload-fsm":
            result = send_action(args.base_url, "unload_fsm", args.holder_id, args.holder_label, args.holder_kind)
        elif args.action == "send-text":
            result = send_action(args.base_url, "send_text", args.holder_id, args.holder_label, args.holder_kind, message=args.message)
        elif args.action == "send-speech":
            result = send_action(args.base_url, "send_speech", args.holder_id, args.holder_label, args.holder_kind, message=args.message)
        else:
            parser.error(f"Unsupported action: {args.action}")
            return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit(result)
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
