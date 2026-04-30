from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from asteria.daemon.common import AsteriaPaths


FSM_TEMPLATE = """from aim_fsm import *


class {class_name}(StateMachineProgram):
    $setup{{
    Say("{spoken_ready}") =C=> Forward(120) =C=> Turn(90) =C=> Say("{spoken_done}")
    }}
"""


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip()).strip("_")
    return cleaned or "asteria_fsm"


def class_name_for(name: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", name)
    camel = "".join(part.capitalize() for part in parts if part)
    return camel or "AsteriaProgram"


def create_fsm_file(paths: AsteriaPaths, name: str, content: str | None = None) -> dict[str, Any]:
    slug = slugify(name)
    target = paths.fsm_root / f"{slug}.fsm"
    target.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        content = FSM_TEMPLATE.format(
            class_name=class_name_for(slug),
            spoken_ready=f"{slug} ready",
            spoken_done=f"{slug} complete",
        )
    target.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "name": slug,
        "fsm_path": str(target),
        "content": content,
    }


def compile_fsm_file(paths: AsteriaPaths, fsm_path: Path) -> dict[str, Any]:
    converter = paths.vex_tools_root / "genfsm"
    if not fsm_path.exists():
        return {"ok": False, "error": f"FSM file not found: {fsm_path}"}
    if not converter.exists():
        return {"ok": False, "error": f"genfsm not found: {converter}"}

    result = subprocess.run(
        [sys.executable, str(converter), str(fsm_path)],
        cwd=str(paths.repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    generated = fsm_path.with_suffix(".py")
    error = None
    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip() or f"genfsm failed with exit code {result.returncode}"
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "fsm_path": str(fsm_path),
        "generated_py": str(generated),
        "generated_exists": generated.exists(),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": error,
    }


def ensure_compiled_fsm(paths: AsteriaPaths, name: str | None = None, fsm_path: Path | None = None) -> dict[str, Any]:
    if fsm_path is None:
        slug = slugify(str(name or "").strip())
        if not slug:
            return {"ok": False, "error": "name or fsm_path is required"}
        fsm_path = paths.fsm_root / f"{slug}.fsm"
    if not fsm_path.exists():
        generated = fsm_path.with_suffix(".py")
        return {
            "ok": generated.exists(),
            "fsm_path": str(fsm_path),
            "generated_py": str(generated),
            "generated_exists": generated.exists(),
            "compiled_now": False,
            "up_to_date": generated.exists(),
        }

    generated = fsm_path.with_suffix(".py")
    needs_compile = not generated.exists() or generated.stat().st_mtime < fsm_path.stat().st_mtime
    if not needs_compile:
        return {
            "ok": True,
            "fsm_path": str(fsm_path),
            "generated_py": str(generated),
            "generated_exists": True,
            "compiled_now": False,
            "up_to_date": True,
        }

    result = compile_fsm_file(paths, fsm_path)
    result["compiled_now"] = bool(result.get("ok"))
    result["up_to_date"] = False
    return result


def _fsm_item(fsm_file: Path) -> dict[str, Any]:
    generated = fsm_file.with_suffix(".py")
    generated_exists = generated.exists()
    return {
        "name": slugify(fsm_file.stem),
        "fsm_path": str(fsm_file),
        "generated_py": str(generated),
        "generated_exists": generated_exists,
        "generated_updated_at_epoch": generated.stat().st_mtime if generated_exists else None,
        "updated_at_epoch": fsm_file.stat().st_mtime,
        "content": fsm_file.read_text(encoding="utf-8"),
    }


def _prefer_fsm_item(candidate: dict[str, Any], current: dict[str, Any], canonical_name: str) -> bool:
    candidate_is_canonical = Path(candidate["fsm_path"]).stem == canonical_name
    current_is_canonical = Path(current["fsm_path"]).stem == canonical_name
    if candidate_is_canonical != current_is_canonical:
        return candidate_is_canonical

    candidate_updated = float(candidate.get("updated_at_epoch") or 0.0)
    current_updated = float(current.get("updated_at_epoch") or 0.0)
    if candidate_updated != current_updated:
        return candidate_updated > current_updated

    candidate_generated = float(candidate.get("generated_updated_at_epoch") or 0.0)
    current_generated = float(current.get("generated_updated_at_epoch") or 0.0)
    if candidate_generated != current_generated:
        return candidate_generated > current_generated

    return str(candidate["fsm_path"]) < str(current["fsm_path"])


def list_fsm_files(paths: AsteriaPaths) -> dict[str, Any]:
    deduped: dict[str, dict[str, Any]] = {}
    for fsm_file in sorted(paths.fsm_root.glob("*.fsm")):
        item = _fsm_item(fsm_file)
        canonical_name = item["name"]
        current = deduped.get(canonical_name)
        if current is None or _prefer_fsm_item(item, current, canonical_name):
            deduped[canonical_name] = item
    items = sorted(deduped.values(), key=lambda item: item["name"])
    return {"ok": True, "items": items}


def write_run_artifact(paths: AsteriaPaths, action: str, payload: dict[str, Any]) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    target = paths.run_root / f"{stamp}-{action}"
    target.mkdir(parents=True, exist_ok=True)
    (target / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(target)
