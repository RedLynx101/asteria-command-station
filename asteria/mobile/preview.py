from __future__ import annotations

import os
import subprocess
from pathlib import Path


def preview_cache_path(source_path: Path, cache_root: Path, width: int, height: int) -> Path:
    safe_stem = source_path.stem.replace(" ", "_")
    return cache_root / f"{safe_stem}-{width}x{height}.rgb565"


def ensure_rgb565_preview(
    source_path: Path,
    cache_root: Path,
    script_path: Path,
    *,
    width: int,
    height: int,
) -> bytes:
    source_path = Path(source_path)
    cache_root = Path(cache_root)
    script_path = Path(script_path)

    if not source_path.exists():
        raise FileNotFoundError(f"image not found: {source_path}")
    if width <= 0 or height <= 0:
        raise ValueError("preview dimensions must be positive")

    cache_root.mkdir(parents=True, exist_ok=True)
    target_path = preview_cache_path(source_path, cache_root, width, height)
    target_size = width * height * 2

    if target_path.exists() and target_path.stat().st_mtime >= source_path.stat().st_mtime:
        data = target_path.read_bytes()
        if len(data) == target_size:
            return data
        target_path.unlink(missing_ok=True)

    if os.name != "nt":
        raise RuntimeError("mobile preview generation currently requires Windows")
    if not script_path.exists():
        raise FileNotFoundError(f"mobile preview generator script is missing: {script_path}")

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-InputPath",
        str(source_path),
        "-OutputPath",
        str(target_path),
        "-Width",
        str(width),
        "-Height",
        str(height),
    ]

    completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown preview generation failure"
        raise RuntimeError(f"preview generation failed: {stderr}")

    data = target_path.read_bytes()
    if len(data) != target_size:
        raise RuntimeError(
            f"preview generation produced {len(data)} bytes, expected {target_size} for {width}x{height} rgb565"
        )
    return data
