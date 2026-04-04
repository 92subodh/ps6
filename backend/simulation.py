"""Simulation utilities for REST and WebSocket streams."""

from __future__ import annotations

import math
import random
from typing import Dict, Generator, Iterable, List, Optional

from digital_twin.swat_process import SWaTDigitalTwin


class SimulationEngine:
    """Generate real-time sensor snapshots for attack theater and MIRROR."""

    def __init__(self, sensor_names: Iterable[str]) -> None:
        self.sensor_names = list(sensor_names)
        self.real_twin = SWaTDigitalTwin(dt=1.0)
        self.decoy_twin = SWaTDigitalTwin(dt=1.0)

    def _stage_indices(self, stage: str) -> List[int]:
        if stage == "P1":
            return list(range(0, min(9, len(self.sensor_names))))
        if stage == "P2":
            return list(range(9, min(17, len(self.sensor_names))))
        if stage == "P3":
            return list(range(17, min(26, len(self.sensor_names))))
        if stage == "P4":
            return list(range(26, min(34, len(self.sensor_names))))
        if stage == "P5":
            return list(range(34, min(43, len(self.sensor_names))))
        return list(range(43, len(self.sensor_names)))

    def _apply_attack_perturbation(
        self,
        twin: SWaTDigitalTwin,
        attack: Dict[str, object],
        timestep: int,
        mode: str,
        overrides: Optional[Dict[str, float]],
    ) -> None:
        sigma = float(attack.get("sigma", 1.0))
        target_stage = str(attack.get("target_stage", "P1"))
        target_indices = self._stage_indices(target_stage)
        twin_keys = list(twin.state.keys())

        perturb_scale = 0.02 + (sigma * 0.012)
        for idx in target_indices[:5]:
            key = twin_keys[idx % len(twin_keys)]
            current_value = float(twin.state[key])
            wave = math.sin((timestep + idx) / 6.0)
            delta = current_value * perturb_scale * wave
            twin.state[key] = current_value + delta

        if mode == "decoy" and overrides:
            for sensor_name, sensor_value in overrides.items():
                if sensor_name not in self.sensor_names:
                    continue
                sensor_idx = self.sensor_names.index(sensor_name)
                key = twin_keys[sensor_idx % len(twin_keys)]
                twin.state[key] = float(sensor_value)

    def _sensor_snapshot(
        self,
        twin: SWaTDigitalTwin,
        attack_id: int,
        timestep: int,
        mode: str,
        target_indices: List[int],
        overrides: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        readings: Dict[str, float] = {}
        base_values = [float(v) for v in twin.state.values()]
        rng_seed = ((attack_id + 1) * 10000) + timestep + (500000 if mode == "decoy" else 0)
        rng = random.Random(rng_seed)

        for idx, sensor_name in enumerate(self.sensor_names):
            base = base_values[idx % len(base_values)]
            phase = math.sin((timestep + idx) / 9.0)
            noise = rng.uniform(-0.02, 0.02) * max(1.0, abs(base))
            stage_flash = 1.0 + (0.02 * phase if idx in target_indices else 0.0)
            value = (base * stage_flash) + noise

            if mode == "decoy" and overrides and sensor_name in overrides:
                value = float(overrides[sensor_name])

            value = max(-1000.0, min(2500.0, value))
            readings[sensor_name] = round(value, 4)

        return readings

    def iter_attack(
        self,
        attack: Dict[str, object],
        duration_seconds: int = 120,
        speed_multiplier: float = 1.0,
        mode: str = "real",
        overrides: Optional[Dict[str, float]] = None,
    ) -> Generator[Dict[str, object], None, None]:
        twin = self.decoy_twin if mode == "decoy" else self.real_twin
        twin.reset()

        attack_id = int(attack.get("attack_id", 0))
        target_stage = str(attack.get("target_stage", "P1"))
        target_indices = self._stage_indices(target_stage)

        for timestep in range(1, duration_seconds + 1):
            self._apply_attack_perturbation(twin, attack, timestep, mode, overrides)
            twin.step({})
            violations = twin.check_safety_constraints()

            alerts = []
            for violation in violations[:4]:
                alerts.append("%s:%s" % (violation.get("type", "violation"), violation.get("sensor", "sensor")))

            if mode == "decoy" and timestep % 15 == 0:
                alerts.append("deception_feedback")

            readings = self._sensor_snapshot(
                twin=twin,
                attack_id=attack_id,
                timestep=timestep,
                mode=mode,
                target_indices=target_indices,
                overrides=overrides,
            )

            yield {
                "mode": mode,
                "attack_id": attack_id,
                "timestep": timestep,
                "speed_multiplier": speed_multiplier,
                "sensor_readings": readings,
                "alerts": alerts,
            }

    def run_attack(
        self,
        attack: Dict[str, object],
        duration_seconds: int = 120,
        speed_multiplier: float = 1.0,
        mode: str = "real",
        overrides: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, object]]:
        return list(
            self.iter_attack(
                attack=attack,
                duration_seconds=duration_seconds,
                speed_multiplier=speed_multiplier,
                mode=mode,
                overrides=overrides,
            )
        )
