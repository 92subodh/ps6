"""Attack recording and feature extraction for MIRROR."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class AttackRecorder:
    """Track attacker actions and derive behavior features in real time."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or (Path(__file__).resolve().parent / "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._session_id = str(uuid.uuid4())
        self._actions: List[Dict[str, Any]] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    def start_new_session(self) -> str:
        with self._lock:
            self._session_id = str(uuid.uuid4())
            self._actions = []
            self._persist()
            return self._session_id

    def log_action(
        self,
        action_type: str,
        sensors_queried: Optional[List[str]] = None,
        command_sent: Optional[str] = None,
        response_observed: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": action_type,
            "target_sensors": sensors_queried or [],
            "command": command_sent,
            "response_observed": response_observed or {},
        }

        with self._lock:
            self._actions.append(entry)
            self._persist()
            return entry

    def actions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._actions)

    def _extract_sensor_index(self, sensor_name: str) -> Optional[int]:
        if sensor_name.startswith("Feature_"):
            suffix = sensor_name.split("_", 1)[1]
            if suffix.isdigit():
                return int(suffix)

        digits = "".join(ch for ch in sensor_name if ch.isdigit())
        if digits:
            return int(digits) % 51
        return None

    def _sensor_stage(self, sensor_name: str) -> str:
        idx = self._extract_sensor_index(sensor_name)
        if idx is None:
            return "P1"
        if idx < 9:
            return "P1"
        if idx < 17:
            return "P2"
        if idx < 26:
            return "P3"
        if idx < 34:
            return "P4"
        if idx < 43:
            return "P5"
        return "P6"

    def compute_behavioral_features(self) -> Dict[str, Any]:
        with self._lock:
            actions = list(self._actions)

        if not actions:
            return {
                "probe_rate": 0.0,
                "target_breadth": 0.0,
                "sequential_score": 0.0,
                "stage_focus": "P1",
                "response_to_alert": 0.0,
                "estimated_skill_level": 0,
                "estimated_objective": "access",
            }

        timestamps = [
            datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            for item in actions
        ]
        elapsed_minutes = max(
            1.0 / 60.0,
            (timestamps[-1] - timestamps[0]).total_seconds() / 60.0,
        )
        probe_rate = len(actions) / elapsed_minutes

        unique_sensors = set()
        stage_counts = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "P5": 0, "P6": 0}
        sensor_indices: List[int] = []

        for action in actions:
            for sensor in action.get("target_sensors", []):
                unique_sensors.add(sensor)
                stage = self._sensor_stage(sensor)
                stage_counts[stage] += 1
                idx = self._extract_sensor_index(sensor)
                if idx is not None:
                    sensor_indices.append(idx)

        target_breadth = len(unique_sensors) / 51.0

        if len(sensor_indices) < 2:
            sequential_score = 0.0
        else:
            in_order = 0
            transitions = len(sensor_indices) - 1
            for i in range(transitions):
                if sensor_indices[i + 1] >= sensor_indices[i]:
                    in_order += 1
            sequential_score = in_order / transitions

        alert_sensitive_events = 0
        for action in actions:
            response = action.get("response_observed", {})
            alerts = response.get("alerts", []) if isinstance(response, dict) else []
            if alerts:
                alert_sensitive_events += 1
        response_to_alert = alert_sensitive_events / len(actions)

        stage_focus = max(stage_counts, key=stage_counts.get)

        objective = "access"
        commands = " ".join(
            [str(item.get("command", "")).lower() for item in actions]
        )
        if any(keyword in commands for keyword in ["set", "drop", "overflow", "shutdown"]):
            objective = "disruption"
        elif any(keyword in commands for keyword in ["dump", "read", "export", "copy"]):
            objective = "data"

        skill_level = 0
        if probe_rate > 10:
            skill_level = 1
        if probe_rate > 20 and target_breadth > 0.25:
            skill_level = 2
        if probe_rate > 30 and target_breadth > 0.5 and sequential_score > 0.5:
            skill_level = 3

        return {
            "probe_rate": round(probe_rate, 2),
            "target_breadth": round(target_breadth, 3),
            "sequential_score": round(sequential_score, 3),
            "stage_focus": stage_focus,
            "response_to_alert": round(response_to_alert, 3),
            "estimated_skill_level": skill_level,
            "estimated_objective": objective,
        }

    def get_status(self) -> Dict[str, Any]:
        features = self.compute_behavioral_features()
        with self._lock:
            actions = list(self._actions)

        return {
            "session_id": self._session_id,
            "total_actions": len(actions),
            "active_probes": [
                action for action in actions[-20:] if action.get("type") in {"probe", "query"}
            ],
            "recent_actions": actions[-30:],
            "behavioral_features": features,
        }

    def _persist(self) -> None:
        session_payload = {
            "session_id": self._session_id,
            "actions": self._actions,
        }
        behavior_payload = self.compute_behavioral_features()

        with (self.output_dir / "attacker_session.json").open("w", encoding="utf-8") as fp:
            json.dump(session_payload, fp, indent=2)

        with (self.output_dir / "behavioral_features.json").open("w", encoding="utf-8") as fp:
            json.dump(behavior_payload, fp, indent=2)
