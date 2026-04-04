"""Data loading and synthetic API payload generation for Layer 5 backend."""

from __future__ import annotations

import json
import random
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataStore:
    """Load local artifacts and expose API-ready views."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.data_dir = data_dir or (self.repo_root / "data" / "synthetic")
        self.generated_dir = self.repo_root / "backend" / "generated"
        self.generated_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._mitigation_rules_path = self.generated_dir / "mitigation_rules.json"

        self.baseline_summary = self._load_json("baseline_results_summary.json", {})
        self.gap_analysis = self._load_json("gap_analysis.json", {})
        self.impact_summary = self._load_json("impact_analysis_summary.json", {})
        self.attack_metadata = self._load_json("synthetic_attacks_metadata.json", {})

        self.sensor_names: List[str] = self.attack_metadata.get("sensor_cols") or [
            "Feature_%d" % i for i in range(51)
        ]

        self.attacks_by_id, self.attack_library = self._build_attack_library()
        self.blindspot_scores = self._build_blindspot_scores()
        self.kill_chains = self._build_kill_chains()
        self.mitigation_rules = self._load_existing_mitigation_rules()

    def _load_json(self, filename: str, default_value: Any) -> Any:
        file_path = self.data_dir / filename
        if not file_path.exists():
            return default_value
        with file_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _load_existing_mitigation_rules(self) -> List[Dict[str, Any]]:
        if not self._mitigation_rules_path.exists():
            return []
        with self._mitigation_rules_path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
            rules = payload.get("rules", []) if isinstance(payload, dict) else []
            return rules if isinstance(rules, list) else []

    def _save_mitigation_rules(self) -> None:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "rules": self.mitigation_rules,
        }
        with self._mitigation_rules_path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2)

    def _detection_rate_by_severity(self) -> Dict[str, float]:
        by_severity = self.baseline_summary.get("by_severity", {})
        severity_rates: Dict[str, float] = {}

        for severity, detector_results in by_severity.items():
            rates: List[float] = []
            if isinstance(detector_results, dict):
                for _, values in detector_results.items():
                    if isinstance(values, dict) and "detection_rate" in values:
                        rates.append(float(values["detection_rate"]))
            severity_rates[severity] = round(sum(rates) / len(rates), 2) if rates else 45.0

        return severity_rates

    def _severity_for_attack_id(self, attack_id: int, n_attacks: int) -> str:
        third = max(1, n_attacks // 3)
        if attack_id < third:
            return "mild"
        if attack_id < third * 2:
            return "moderate"
        return "severe"

    def _attack_type_for_index(self, attack_id: int) -> str:
        attack_types = ["vae_boundary", "cgan_novel", "lstm_drift"]
        return attack_types[attack_id % len(attack_types)]

    def _parse_affected_stages(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
            return [part for part in parts if part]
        return []

    def _rank_score(self, impact_score: float, detection_rate: float) -> float:
        return round((0.7 * impact_score) + (0.3 * (100.0 - detection_rate)), 3)

    def _stage_from_affected(self, affected_stages: List[str], attack_id: int) -> str:
        for stage in affected_stages:
            if stage in {"P1", "P2", "P3", "P4", "P5", "P6"}:
                return stage
        return "P%d" % ((attack_id % 6) + 1)

    def _build_seed_attack(
        self,
        raw_attack: Dict[str, Any],
        gap_lookup: Dict[int, Dict[str, Any]],
        detection_by_severity: Dict[str, float],
    ) -> Dict[str, Any]:
        attack_id = int(raw_attack.get("attack_id", 0))
        severity = str(raw_attack.get("severity_level", "mild"))
        sigma = float(raw_attack.get("sigma", {"mild": 1.0, "moderate": 2.0, "severe": 3.0}.get(severity, 1.0)))
        impact_score = float(raw_attack.get("impact_score", 65.0))
        affected_stages = self._parse_affected_stages(raw_attack.get("affected_stages", []))

        gap_entry = gap_lookup.get(attack_id)
        detection_rate = float(gap_entry.get("detection_rate", detection_by_severity.get(severity, 45.0))) if gap_entry else float(detection_by_severity.get(severity, 45.0))

        attack_type = self._attack_type_for_index(attack_id)
        target_stage = self._stage_from_affected(affected_stages, attack_id)

        entry = {
            "attack_id": attack_id,
            "severity_level": severity,
            "sigma": sigma,
            "impact_score": round(impact_score, 3),
            "detection_rate": round(detection_rate, 3),
            "attack_type": attack_type,
            "source": "historical_seed",
            "target_stage": target_stage,
            "affected_stages": affected_stages or [target_stage],
            "total_violations": int(raw_attack.get("total_violations", 0)),
            "primary_violation": str(raw_attack.get("primary_violation", "unknown")),
            "detected_by": gap_entry.get("detected_by", []) if gap_entry else [],
        }
        entry["rank_score"] = self._rank_score(entry["impact_score"], entry["detection_rate"])
        entry["description"] = "Synthetic attack focused on %s (%s)." % (target_stage, attack_type)
        return entry

    def _build_attack_library(self) -> tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
        n_attacks = int(self.attack_metadata.get("n_attacks", 120))
        if n_attacks <= 0:
            n_attacks = 120

        impact_top = self.impact_summary.get("top_attacks", [])
        gap_top = self.gap_analysis.get("top_gaps", [])
        gap_lookup = {
            int(item.get("attack_id", -1)): item
            for item in gap_top
            if isinstance(item, dict) and "attack_id" in item
        }

        detection_by_severity = self._detection_rate_by_severity()

        attacks_by_id: Dict[int, Dict[str, Any]] = {}

        for raw_attack in impact_top:
            if not isinstance(raw_attack, dict):
                continue
            entry = self._build_seed_attack(raw_attack, gap_lookup, detection_by_severity)
            attacks_by_id[entry["attack_id"]] = entry

        for attack_id in range(n_attacks):
            if attack_id in attacks_by_id:
                continue

            rng = random.Random((attack_id + 1) * 41)
            severity = self._severity_for_attack_id(attack_id, n_attacks)
            sigma = {"mild": 1.0, "moderate": 2.0, "severe": 3.0}[severity]

            if severity == "mild":
                impact_score = rng.uniform(45.0, 96.0)
            elif severity == "moderate":
                impact_score = rng.uniform(52.0, 88.0)
            else:
                impact_score = rng.uniform(58.0, 93.0)

            detection_base = detection_by_severity.get(severity, 45.0)
            detection_rate = max(0.0, min(100.0, detection_base + rng.uniform(-16.0, 14.0)))

            target_stage = "P%d" % ((attack_id % 6) + 1)
            if impact_score > 82.0:
                affected_stages = [target_stage, "P%d" % (((attack_id + 2) % 6) + 1)]
            else:
                affected_stages = [target_stage]

            attack_type = self._attack_type_for_index(attack_id)

            entry = {
                "attack_id": attack_id,
                "severity_level": severity,
                "sigma": sigma,
                "impact_score": round(impact_score, 3),
                "detection_rate": round(detection_rate, 3),
                "attack_type": attack_type,
                "source": "generated_profile",
                "target_stage": target_stage,
                "affected_stages": affected_stages,
                "total_violations": int(rng.uniform(800, 2600)),
                "primary_violation": random.choice([
                    "ph_violation",
                    "chlorine_high",
                    "tank_overflow",
                    "pump_deadheading",
                ]),
                "detected_by": [],
            }
            entry["rank_score"] = self._rank_score(entry["impact_score"], entry["detection_rate"])
            entry["description"] = "Model-generated attack profile (%s, %s)." % (severity, attack_type)
            attacks_by_id[attack_id] = entry

        attack_library = sorted(
            attacks_by_id.values(), key=lambda item: item["rank_score"], reverse=True
        )

        return attacks_by_id, attack_library

    def _build_blindspot_scores(self) -> Dict[str, float]:
        stage_counts = {"P1": 1, "P2": 1, "P3": 1, "P4": 1, "P5": 1, "P6": 1}
        for gap in self.gap_analysis.get("top_gaps", []):
            for stage in self._parse_affected_stages(gap.get("affected_stages", "")):
                if stage in stage_counts:
                    stage_counts[stage] += 1

        max_count = max(stage_counts.values())
        rng = random.Random(2026)

        blindspot_scores: Dict[str, float] = {}
        for idx, sensor_name in enumerate(self.sensor_names):
            stage = "P1"
            if idx >= 43:
                stage = "P6"
            elif idx >= 34:
                stage = "P5"
            elif idx >= 26:
                stage = "P4"
            elif idx >= 17:
                stage = "P3"
            elif idx >= 9:
                stage = "P2"

            stage_risk = 4.2 * (stage_counts[stage] / max_count)
            score = 1.7 + stage_risk + rng.uniform(-0.8, 2.6)
            blindspot_scores[sensor_name] = round(max(0.4, min(9.9, score)), 2)

        return blindspot_scores

    def _build_kill_chains(self) -> List[Dict[str, Any]]:
        chains = []
        for item in self.attack_library[:10]:
            stage = item.get("target_stage", "P1")
            chain = [
                "Initial Access",
                "Manipulate sensors in %s" % stage,
                "Cross-stage propagation",
                "Safety envelope violation",
            ]
            chains.append(
                {
                    "attack_id": item["attack_id"],
                    "rank_score": item["rank_score"],
                    "chain": chain,
                    "blast_radius": round(item["impact_score"] / 10.0, 2),
                }
            )
        return chains

    def _stage_indices(self, stage: str) -> List[int]:
        if stage == "P1":
            return list(range(0, 9))
        if stage == "P2":
            return list(range(9, 17))
        if stage == "P3":
            return list(range(17, 26))
        if stage == "P4":
            return list(range(26, 34))
        if stage == "P5":
            return list(range(34, 43))
        return list(range(43, min(51, len(self.sensor_names))))

    def get_attack_library(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        attacks = [dict(item) for item in self.attack_library]
        return attacks[:limit] if limit else attacks

    def get_attack(self, attack_id: int) -> Optional[Dict[str, Any]]:
        attack = self.attacks_by_id.get(attack_id)
        return dict(attack) if attack else None

    def get_blindspot_scores(self) -> Dict[str, float]:
        return dict(self.blindspot_scores)

    def get_kill_chains(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self.kill_chains]

    def get_shap_explanation(self, attack_id: int) -> Dict[str, Any]:
        attack = self.attacks_by_id.get(attack_id)
        if not attack:
            raise KeyError("Attack not found")

        rng = random.Random((attack_id + 7) * 31)
        target_stage = attack.get("target_stage", "P1")
        target_indices = self._stage_indices(target_stage)
        candidate_indices = target_indices + [
            idx for idx in range(len(self.sensor_names)) if idx not in target_indices
        ]

        top_indices = candidate_indices[:3] + random.sample(candidate_indices[3:], 2)

        top_features = []
        for idx in top_indices:
            value = round(rng.uniform(0.12, 0.55), 3)
            direction = "increase" if rng.random() > 0.35 else "decrease"
            top_features.append(
                {
                    "sensor": self.sensor_names[idx],
                    "shap_value": value,
                    "direction": direction,
                }
            )

        top_features.sort(key=lambda item: item["shap_value"], reverse=True)

        return {
            "attack_id": attack_id,
            "top_features": top_features,
            "summary": "Model confidence points to %s as the primary impact region." % target_stage,
        }

    def get_lime_rule(self, attack_id: int) -> Dict[str, Any]:
        shap = self.get_shap_explanation(attack_id)
        top_features = shap.get("top_features", [])[:2]
        if len(top_features) < 2:
            top_features = top_features + [
                {"sensor": self.sensor_names[0], "direction": "increase", "shap_value": 0.2}
            ]

        rng = random.Random((attack_id + 3) * 101)
        threshold_a = round(rng.uniform(0.55, 0.9), 3)
        threshold_b = round(rng.uniform(0.2, 0.45), 3)

        sensor_a = top_features[0]["sensor"]
        sensor_b = top_features[1]["sensor"]

        return {
            "attack_id": attack_id,
            "condition_text": "IF %s > %.3f AND %s < %.3f THEN flag anomaly"
            % (sensor_a, threshold_a, sensor_b, threshold_b),
            "sensors_involved": [sensor_a, sensor_b],
            "threshold_dict": {
                sensor_a: {"op": ">", "value": threshold_a},
                sensor_b: {"op": "<", "value": threshold_b},
            },
            "confidence": round(rng.uniform(0.62, 0.91), 3),
        }

    def get_gaps(self, limit: int = 60) -> List[Dict[str, Any]]:
        gap_list: List[Dict[str, Any]] = []

        raw_gaps = self.gap_analysis.get("top_gaps", [])
        for item in raw_gaps:
            if not isinstance(item, dict):
                continue
            attack_id = int(item.get("attack_id", -1))
            if attack_id < 0:
                continue
            lime_rule = self.get_lime_rule(attack_id)
            gap_item = dict(item)
            gap_item["lime_rule"] = lime_rule
            gap_list.append(gap_item)

        if not gap_list:
            for attack in self.attack_library:
                if attack["impact_score"] > 70.0 and attack["detection_rate"] < 30.0:
                    gap_item = {
                        "attack_id": attack["attack_id"],
                        "severity_level": attack["severity_level"],
                        "impact_score": attack["impact_score"],
                        "detection_rate": attack["detection_rate"],
                        "detected_by": attack.get("detected_by", []),
                        "gap_type": "synthetic_gap",
                        "affected_stages": ", ".join(attack.get("affected_stages", [])),
                        "primary_violation": attack.get("primary_violation", "unknown"),
                        "total_violations": attack.get("total_violations", 0),
                        "lime_rule": self.get_lime_rule(int(attack["attack_id"])),
                    }
                    gap_list.append(gap_item)

        gap_list.sort(key=lambda item: float(item.get("impact_score", 0.0)), reverse=True)
        return gap_list[:limit]

    def get_mitigation_rules(self) -> List[Dict[str, Any]]:
        return [dict(rule) for rule in self.mitigation_rules]

    def apply_fix(self, attack_id: int) -> Dict[str, Any]:
        with self._lock:
            attack = self.attacks_by_id.get(attack_id)
            if not attack:
                raise KeyError("Attack not found")

            before_detection = float(attack["detection_rate"])
            rng = random.Random((attack_id + 11) * 73)
            improvement = round(rng.uniform(8.0, 24.0), 3)
            after_detection = round(min(100.0, before_detection + improvement), 3)
            attack["detection_rate"] = after_detection
            attack["rank_score"] = self._rank_score(attack["impact_score"], after_detection)

            shap = self.get_shap_explanation(attack_id)
            impacted_sensors = [item["sensor"] for item in shap.get("top_features", [])[:2]]

            before_blindspot = [self.blindspot_scores.get(sensor, 0.0) for sensor in impacted_sensors]
            for sensor in impacted_sensors:
                current = self.blindspot_scores.get(sensor, 0.0)
                adjusted = max(0.1, current - (improvement / 20.0))
                self.blindspot_scores[sensor] = round(adjusted, 3)
            after_blindspot = [self.blindspot_scores.get(sensor, 0.0) for sensor in impacted_sensors]

            rule_payload = self.get_lime_rule(attack_id)
            rule_entry = {
                "rule_id": "rule_%d_%d" % (attack_id, len(self.mitigation_rules) + 1),
                "attack_id": attack_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "condition_text": rule_payload["condition_text"],
                "sensors_involved": rule_payload["sensors_involved"],
                "threshold_dict": rule_payload["threshold_dict"],
                "confidence": rule_payload["confidence"],
                "attacks_covered": [attack_id],
            }

            self.mitigation_rules.append(rule_entry)
            self._save_mitigation_rules()

            self.attack_library = sorted(
                self.attacks_by_id.values(),
                key=lambda item: item["rank_score"],
                reverse=True,
            )
            self.kill_chains = self._build_kill_chains()

            if before_blindspot:
                improvement_metric = round(
                    (sum(before_blindspot) / len(before_blindspot))
                    - (sum(after_blindspot) / len(after_blindspot)),
                    3,
                )
            else:
                improvement_metric = round(improvement / 20.0, 3)

            return {
                "attack_id": attack_id,
                "before_detection_rate": before_detection,
                "after_detection_rate": after_detection,
                "rule_generated": rule_entry,
                "improvement_metric": improvement_metric,
                "updated_blindspot_scores": {
                    sensor: self.blindspot_scores[sensor] for sensor in impacted_sensors
                },
            }
