"""Attacker genome profiling for MIRROR."""

from __future__ import annotations

from typing import Dict, List


class AttackerGenomeEngine:
    """Classify attacker behavior into high-level archetypes."""

    RESPONSE_MAP = {
        "Nation-State Actor": "Initiate forensic investigation for last 30 days.",
        "Ransomware Group": "Isolate affected segment within 60 seconds.",
        "Insider Threat": "Revoke credentials and rotate privileged keys immediately.",
        "Script Kiddie": "Log activity and maintain deception environment.",
    }

    def classify(self, features: Dict[str, float]) -> Dict[str, object]:
        """Return archetype, confidence, and response guidance."""
        probe_rate = float(features.get("probe_rate", 0.0))
        target_breadth = float(features.get("target_breadth", 0.0))
        sequential_score = float(features.get("sequential_score", 0.0))
        skill_level = int(features.get("estimated_skill_level", 0))
        objective = str(features.get("estimated_objective", "access"))

        if objective == "disruption" and probe_rate > 18 and skill_level >= 2:
            archetype = "Ransomware Group"
            confidence = 0.78
        elif objective == "data" and target_breadth > 0.45 and sequential_score > 0.55:
            archetype = "Nation-State Actor"
            confidence = 0.82
        elif skill_level >= 2 and target_breadth < 0.25 and sequential_score > 0.6:
            archetype = "Insider Threat"
            confidence = 0.74
        else:
            archetype = "Script Kiddie"
            confidence = 0.67

        confidence += min(0.12, probe_rate / 400.0)
        confidence = round(min(0.95, max(0.55, confidence)), 2)

        evidence: List[str] = [
            "Probe rate: %.2f actions/min" % probe_rate,
            "Target breadth: %.2f of plant sensors" % target_breadth,
            "Sequential score: %.2f" % sequential_score,
            "Estimated skill level: %d/3" % skill_level,
        ]

        return {
            "archetype": archetype,
            "confidence": confidence,
            "recommended_response": self.RESPONSE_MAP[archetype],
            "behavioral_evidence": evidence,
        }
