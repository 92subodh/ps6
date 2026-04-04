"""Submission validation checks for Person 3 deliverables.

This script validates:
- Layer 5 backend REST APIs
- Layer 5 backend WebSocket streams
- Persistence artifacts for mitigation rules and MIRROR recorder logs

Usage:
    python validate_person3.py
    python validate_person3.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request

import websockets


Result = Tuple[bool, str, str]


def _record(results: List[Result], ok: bool, check_name: str, details: str) -> None:
    results.append((ok, check_name, details))


def _http_json(
    method: str,
    url: str,
    payload: Dict[str, Any] | None = None,
    timeout: float = 12.0,
) -> Dict[str, Any] | List[Any]:
    data: bytes | None = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=data, headers=headers, method=method)

    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Cannot reach {url}: {exc.reason}") from exc


def run_rest_checks(base_url: str, repo_root: Path) -> List[Result]:
    results: List[Result] = []

    health = _http_json("GET", f"{base_url}/health")
    ok_health = (
        isinstance(health, dict)
        and health.get("status") == "ok"
        and int(health.get("attacks_loaded", 0)) > 0
        and int(health.get("sensors", 0)) > 0
    )
    _record(results, ok_health, "REST /health", f"status={health}")

    attacks = _http_json("GET", f"{base_url}/attacks?limit=3")
    ok_attacks = (
        isinstance(attacks, list)
        and len(attacks) > 0
        and all("attack_id" in item and "attack_type" in item for item in attacks if isinstance(item, dict))
    )
    _record(results, ok_attacks, "REST /attacks", f"count={len(attacks) if isinstance(attacks, list) else 'invalid'}")

    blindspots = _http_json("GET", f"{base_url}/blindspot-scores")
    ok_blindspots = isinstance(blindspots, dict) and len(blindspots) > 0
    _record(results, ok_blindspots, "REST /blindspot-scores", f"sensors={len(blindspots) if isinstance(blindspots, dict) else 'invalid'}")

    what_if = _http_json(
        "POST",
        f"{base_url}/what-if",
        payload={
            "natural_language_query": "What if P2 sees drift attack during high flow?",
        },
    )
    generated_attack_id = -1
    if isinstance(what_if, dict):
        generated_attack = what_if.get("attack_generated", {})
        if isinstance(generated_attack, dict):
            generated_attack_id = int(generated_attack.get("attack_id", -1))

    ok_what_if = isinstance(what_if, dict) and generated_attack_id >= 0
    _record(results, ok_what_if, "REST /what-if", f"attack_id={generated_attack_id}")

    if generated_attack_id < 0:
        generated_attack_id = 0

    fix_result = _http_json("POST", f"{base_url}/apply-fix/{generated_attack_id}")
    ok_fix = (
        isinstance(fix_result, dict)
        and "before_detection_rate" in fix_result
        and "after_detection_rate" in fix_result
    )
    _record(
        results,
        ok_fix,
        "REST /apply-fix/{attack_id}",
        f"attack_id={generated_attack_id}",
    )

    probe_result = _http_json(
        "POST",
        f"{base_url}/attacker/probe",
        payload={
            "query_type": "probe",
            "sensors_queried": ["Feature_7", "Feature_9"],
            "command_sent": "set Feature_7 to 0.95",
        },
    )
    ok_probe = isinstance(probe_result, dict) and bool(probe_result.get("intercepted"))
    _record(results, ok_probe, "REST /attacker/probe", f"intercepted={probe_result.get('intercepted') if isinstance(probe_result, dict) else 'invalid'}")

    mirror_status = _http_json("GET", f"{base_url}/mirror/status")
    ok_mirror_status = isinstance(mirror_status, dict) and int(mirror_status.get("total_actions", 0)) >= 1
    _record(
        results,
        ok_mirror_status,
        "REST /mirror/status",
        f"total_actions={mirror_status.get('total_actions') if isinstance(mirror_status, dict) else 'invalid'}",
    )

    mitigation_path = repo_root / "backend" / "generated" / "mitigation_rules.json"
    mirror_session_path = repo_root / "mirror" / "output" / "attacker_session.json"

    mitigation_ok = False
    mitigation_detail = "missing"
    if mitigation_path.exists():
        try:
            with mitigation_path.open("r", encoding="utf-8") as fp:
                mitigation_payload = json.load(fp)
            rules = mitigation_payload.get("rules", []) if isinstance(mitigation_payload, dict) else []
            mitigation_ok = isinstance(rules, list) and len(rules) > 0
            mitigation_detail = f"rules={len(rules) if isinstance(rules, list) else 'invalid'}"
        except (OSError, json.JSONDecodeError) as exc:
            mitigation_detail = f"error={exc}"
    _record(results, mitigation_ok, "File backend/generated/mitigation_rules.json", mitigation_detail)

    mirror_file_ok = False
    mirror_file_detail = "missing"
    if mirror_session_path.exists():
        try:
            with mirror_session_path.open("r", encoding="utf-8") as fp:
                mirror_payload = json.load(fp)
            actions = mirror_payload.get("actions", []) if isinstance(mirror_payload, dict) else []
            mirror_file_ok = isinstance(actions, list) and len(actions) > 0
            mirror_file_detail = f"actions={len(actions) if isinstance(actions, list) else 'invalid'}"
        except (OSError, json.JSONDecodeError) as exc:
            mirror_file_detail = f"error={exc}"
    _record(results, mirror_file_ok, "File mirror/output/attacker_session.json", mirror_file_detail)

    return results


async def _ws_check(url: str, minimum_frames: int = 2) -> Tuple[bool, str]:
    required_fields = {"mode", "attack_id", "timestep", "sensor_readings", "alerts"}

    try:
        async with websockets.connect(url, open_timeout=10, close_timeout=2) as socket:
            for frame_index in range(minimum_frames):
                raw_payload = await asyncio.wait_for(socket.recv(), timeout=8)
                payload = json.loads(raw_payload)
                if not isinstance(payload, dict):
                    return False, f"frame {frame_index + 1} is not a JSON object"
                missing = sorted(required_fields - set(payload.keys()))
                if missing:
                    return False, f"frame {frame_index + 1} missing fields: {', '.join(missing)}"
        return True, f"received {minimum_frames} valid frames"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


async def run_ws_checks(base_url: str) -> List[Result]:
    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    checks = [
        (
            "WebSocket /ws/simulation",
            f"{ws_base}/ws/simulation?attack_id=0&speed=2&duration=8",
            2,
        ),
        (
            "WebSocket /ws/decoy",
            f"{ws_base}/ws/decoy?attack_id=0&speed=2&duration=8",
            1,
        ),
        (
            "WebSocket /ws/real",
            f"{ws_base}/ws/real?attack_id=0&speed=2&duration=8",
            1,
        ),
    ]

    results: List[Result] = []
    for check_name, ws_url, minimum_frames in checks:
        ok, details = await _ws_check(ws_url, minimum_frames=minimum_frames)
        _record(results, ok, check_name, details)

    return results


def print_results(results: List[Result]) -> int:
    print("=" * 80)
    print("PERSON 3 VALIDATION REPORT")
    print("=" * 80)

    failures = 0
    for ok, check_name, details in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {check_name}")
        print(f"       {details}")
        if not ok:
            failures += 1

    print("-" * 80)
    print(f"Total checks: {len(results)}")
    print(f"Passed: {len(results) - failures}")
    print(f"Failed: {failures}")

    if failures == 0:
        print("Result: READY FOR SUBMISSION DEMO")
    else:
        print("Result: NOT READY - fix failed checks before demo")

    print("=" * 80)
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Person 3 backend/frontend integration readiness")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for backend API (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent),
        help="Repository root path used for persistence artifact checks",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    try:
        rest_results = run_rest_checks(args.base_url.rstrip("/"), repo_root)
    except Exception as exc:  # noqa: BLE001
        print(f"Validation aborted during REST checks: {exc}")
        return 1

    try:
        ws_results = asyncio.run(run_ws_checks(args.base_url.rstrip("/")))
    except Exception as exc:  # noqa: BLE001
        print(f"Validation aborted during WebSocket checks: {exc}")
        return 1

    all_results = rest_results + ws_results
    failures = print_results(all_results)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
