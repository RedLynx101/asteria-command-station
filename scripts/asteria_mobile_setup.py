#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from asteria.mobile.auth import make_auth_config, redact_token, token_fingerprint


def detect_lan_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Asteria DS mobile auth + import config.")
    parser.add_argument("--out-dir", default="asteria/artifacts/mobile-config", help="Directory for laptop-side config output.")
    parser.add_argument("--device-name", default="Asteria DS", help="Human-friendly mobile device name.")
    parser.add_argument("--mobile-port", default=8766, type=int, help="Asteria daemon port.")
    parser.add_argument("--holder-id", default="asteria-ds", help="Lease holder id.")
    parser.add_argument("--holder-label", default="Asteria DS", help="Lease holder label.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    auth = make_auth_config(device_name=args.device_name)
    auth.holder_id = args.holder_id
    auth.holder_label = args.holder_label

    lan_ip = detect_lan_ip()
    daemon_base_url = f"http://{lan_ip}:{args.mobile_port}"

    laptop_config = {
        "device_name": auth.device_name,
        "token_fingerprint": token_fingerprint(auth.device_token),
        "holder_id": auth.holder_id,
        "holder_label": auth.holder_label,
        "daemon_base_url": daemon_base_url,
    }

    import_config = {
        "daemon_base_url": daemon_base_url,
        "device_token": auth.device_token,
        "holder_id": auth.holder_id,
        "holder_label": auth.holder_label,
        "theme": "light_asteria",
        "sounds_enabled": True,
        "kick_style": "medium",
    }

    (out_dir / "mobile-auth.json").write_text(json.dumps(asdict(auth), indent=2))
    (out_dir / "mobile-laptop-config.json").write_text(json.dumps(laptop_config, indent=2))
    (out_dir / "asteria-ds-import-config.json").write_text(json.dumps(import_config, indent=2))

    print("Asteria DS mobile config generated.")
    print(f"LAN base URL: {daemon_base_url}")
    print(f"Token: {redact_token(auth.device_token)}")
    print(f"Import file: {(out_dir / 'asteria-ds-import-config.json').resolve()}")


if __name__ == "__main__":
    main()
