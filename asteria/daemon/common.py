from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AsteriaPaths:
    repo_root: Path
    asteria_root: Path
    gui_root: Path
    vex_tools_root: Path
    aim_ws_root: Path
    artifacts_root: Path
    fsm_root: Path
    image_root: Path
    run_root: Path


def repo_root() -> Path:
    env_root = os.getenv("REPO_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if (root / "vex-aim-tools").exists():
            return root
    return Path(__file__).resolve().parents[2]


def resolve_paths() -> AsteriaPaths:
    root = repo_root()
    asteria_root = root / "asteria"
    artifacts_root = asteria_root / "artifacts"
    return AsteriaPaths(
        repo_root=root,
        asteria_root=asteria_root,
        gui_root=asteria_root / "gui",
        vex_tools_root=root / "vex-aim-tools",
        aim_ws_root=root / "AIM_Websocket_Library",
        artifacts_root=artifacts_root,
        fsm_root=artifacts_root / "fsm",
        image_root=artifacts_root / "images",
        run_root=artifacts_root / "runs",
    )


def ensure_dirs(paths: AsteriaPaths) -> None:
    for directory in (
        paths.artifacts_root,
        paths.fsm_root,
        paths.image_root,
        paths.run_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_import_paths(paths: AsteriaPaths) -> None:
    for candidate in (
        paths.vex_tools_root,
        paths.vex_tools_root / "aim_fsm",
        paths.aim_ws_root,
        paths.fsm_root,
    ):
        text = str(candidate)
        if text not in sys.path:
            sys.path.insert(0, text)


def parse_hosts(explicit_host: str | None = None) -> list[str]:
    raw_hosts = [
        explicit_host or "",
        os.getenv("ROBOT", ""),
        os.getenv("OPENCLAW_VEX_AIM_HOST_FALLBACKS", ""),
        "192.168.4.1",
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for raw in raw_hosts:
        for item in raw.split(","):
            host = item.strip()
            if not host or host in seen:
                continue
            deduped.append(host)
            seen.add(host)
    return deduped


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
