"""FastAPI backend for Layer 5 dashboard and MIRROR services."""

from __future__ import annotations

import asyncio
import random
import re
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.data_store import DataStore
from backend.simulation import SimulationEngine
from mirror.profile import AttackerGenomeEngine
from mirror.recorder import AttackRecorder


class SimulateRequest(BaseModel):
    attack_id: int = Field(..., ge=0)
    duration_seconds: int = Field(default=120, ge=10, le=600)
    speed_multiplier: float = Field(default=1.0, ge=0.5, le=5.0)


class WhatIfRequest(BaseModel):
    natural_language_query: str = Field(min_length=3, max_length=500)


class ProbeRequest(BaseModel):
    query_type: str = Field(default="probe")
    sensors_queried: List[str] = Field(default_factory=list)
    command_sent: Optional[str] = None


app = FastAPI(
    title="GenTwin Layer 5 API",
    description="FastAPI backend for dashboard, simulation, and MIRROR deception streams.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DataStore()
simulator = SimulationEngine(store.sensor_names)
recorder = AttackRecorder()
genome = AttackerGenomeEngine()

what_if_cache: Dict[str, Dict[str, object]] = {}
decoy_overrides: Dict[str, float] = {}


def _parse_attack_type(query: str) -> Optional[str]:
    normalized = query.lower()
    if "drift" in normalized:
        return "lstm_drift"
    if "spike" in normalized or "novel" in normalized:
        return "cgan_novel"
    if "boundary" in normalized or "replay" in normalized:
        return "vae_boundary"
    return None


def _parse_stage(query: str) -> Optional[str]:
    match = re.search(r"\bP([1-6])\b", query.upper())
    if not match:
        return None
    return "P%s" % match.group(1)


def _pick_attack_for_query(query: str) -> Dict[str, object]:
    stage = _parse_stage(query)
    attack_type = _parse_attack_type(query)

    for attack in store.get_attack_library():
        if stage and attack.get("target_stage") != stage:
            continue
        if attack_type and attack.get("attack_type") != attack_type:
            continue
        return attack

    for attack in store.get_attack_library():
        if stage and attack.get("target_stage") == stage:
            return attack

    attacks = store.get_attack_library(limit=1)
    if not attacks:
        raise HTTPException(status_code=404, detail="No attacks available")
    return attacks[0]


def _generate_what_if_result(query: str) -> Dict[str, object]:
    attack = _pick_attack_for_query(query)
    quick_log = simulator.run_attack(
        attack=attack,
        duration_seconds=40,
        speed_multiplier=2.0,
        mode="real",
    )

    alerts = []
    for item in quick_log:
        alerts.extend(item.get("alerts", []))
    unique_alerts = sorted(set(alerts))

    cascade_chain = [
        "Initial access",
        "Sensor manipulation in %s" % attack.get("target_stage", "P1"),
        "Cross-stage deviation",
        "Safety threshold pressure",
    ]

    time_to_failure = max(3, int(20 - float(attack.get("sigma", 1.0)) * 4))

    return {
        "attack_generated": attack,
        "affected_sensors": store.get_shap_explanation(int(attack["attack_id"]))["top_features"],
        "detected": len(unique_alerts) > 0,
        "cascade_chain": cascade_chain,
        "time_to_failure": time_to_failure,
        "recommended_fix": store.get_lime_rule(int(attack["attack_id"])),
        "plain_english_summary": (
            "Scenario routed to attack %d targeting %s. "
            "Estimated time-to-failure is %d minutes with %d active alert types."
            % (
                int(attack["attack_id"]),
                str(attack.get("target_stage", "P1")),
                time_to_failure,
                len(unique_alerts),
            )
        ),
        "simulation_excerpt": quick_log[-5:],
    }


@app.on_event("startup")
async def prewarm_what_if_cache() -> None:
    templates = []
    stage_tokens = ["P1", "P2", "P3", "P4", "P5", "P6"]
    type_tokens = ["drift", "spike", "replay"]

    for stage in stage_tokens:
        for attack_type in type_tokens:
            templates.append("What if %s sensors are under %s attack during peak flow?" % (stage, attack_type))

    templates = templates[:20]
    for query in templates:
        what_if_cache[query.lower()] = _generate_what_if_result(query)


@app.get("/health")
async def health() -> Dict[str, object]:
    return {
        "status": "ok",
        "attacks_loaded": len(store.get_attack_library()),
        "sensors": len(store.sensor_names),
        "mirror_session": recorder.session_id,
    }


@app.get("/attacks")
async def get_attacks(limit: int = 200) -> List[Dict[str, object]]:
    return store.get_attack_library(limit=limit)


@app.get("/attacks/{attack_id}")
async def get_attack(attack_id: int) -> Dict[str, object]:
    attack = store.get_attack(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")
    return attack


@app.post("/simulate")
async def simulate_attack(request: SimulateRequest) -> Dict[str, object]:
    attack = store.get_attack(request.attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    simulation_log = await asyncio.to_thread(
        simulator.run_attack,
        attack,
        request.duration_seconds,
        request.speed_multiplier,
        "real",
        None,
    )

    return {
        "attack": attack,
        "simulation_log": simulation_log,
    }


@app.get("/blindspot-scores")
async def get_blindspot_scores() -> Dict[str, float]:
    return store.get_blindspot_scores()


@app.get("/kill-chains")
async def get_kill_chains() -> List[Dict[str, object]]:
    return store.get_kill_chains()


@app.get("/shap/{attack_id}")
async def get_shap(attack_id: int) -> Dict[str, object]:
    try:
        return store.get_shap_explanation(attack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/lime/{attack_id}")
async def get_lime(attack_id: int) -> Dict[str, object]:
    try:
        return store.get_lime_rule(attack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/gaps")
async def get_gaps(limit: int = 60) -> Dict[str, object]:
    gaps = store.get_gaps(limit=limit)
    return {
        "total": len(gaps),
        "gaps": gaps,
    }


@app.post("/what-if")
async def what_if(request: WhatIfRequest) -> Dict[str, object]:
    query_key = request.natural_language_query.strip().lower()
    if query_key in what_if_cache:
        return what_if_cache[query_key]

    result = await asyncio.to_thread(_generate_what_if_result, request.natural_language_query)
    what_if_cache[query_key] = result
    return result


@app.post("/apply-fix/{attack_id}")
async def apply_fix(attack_id: int) -> Dict[str, object]:
    try:
        payload = store.apply_fix(attack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return payload


@app.post("/attacker/probe")
async def attacker_probe(request: ProbeRequest) -> Dict[str, object]:
    command_text = (request.command_sent or "").strip()
    sensors = list(request.sensors_queried)

    if "reset" in command_text.lower() or "clear" in command_text.lower():
        decoy_overrides.clear()

    override_pattern = re.compile(r"(Feature_\d+)\s*(?:=|to)\s*([+-]?\d+(?:\.\d+)?)", re.IGNORECASE)
    for sensor_name, value_text in override_pattern.findall(command_text):
        if sensor_name not in store.sensor_names:
            continue
        decoy_overrides[sensor_name] = float(value_text)
        if sensor_name not in sensors:
            sensors.append(sensor_name)

    await asyncio.sleep(random.uniform(0.05, 0.2))

    default_attack = store.get_attack(0) or store.get_attack_library(limit=1)[0]
    decoy_snapshot = simulator.run_attack(
        attack=default_attack,
        duration_seconds=1,
        speed_multiplier=1.0,
        mode="decoy",
        overrides=decoy_overrides,
    )[-1]

    log_entry = recorder.log_action(
        action_type=request.query_type,
        sensors_queried=sensors,
        command_sent=command_text,
        response_observed={
            "alerts": decoy_snapshot.get("alerts", []),
            "sample": dict(list(decoy_snapshot.get("sensor_readings", {}).items())[:5]),
        },
    )

    status = recorder.get_status()
    profile = genome.classify(status["behavioral_features"])

    return {
        "intercepted": True,
        "redirected_to": "fake_plant",
        "decoy_response": decoy_snapshot,
        "active_overrides": decoy_overrides,
        "logged_action": log_entry,
        "attacker_profile": profile,
    }


@app.get("/mirror/status")
async def mirror_status() -> Dict[str, object]:
    status = recorder.get_status()
    status["attacker_profile"] = genome.classify(status["behavioral_features"])
    status["patches_deployed"] = len(store.get_mitigation_rules())
    return status


@app.get("/mirror/profile")
async def mirror_profile() -> Dict[str, object]:
    features = recorder.compute_behavioral_features()
    profile = genome.classify(features)
    return {
        "features": features,
        "profile": profile,
    }


async def _stream_to_websocket(
    websocket: WebSocket,
    attack: Dict[str, object],
    mode: str,
    duration_seconds: int,
    speed_multiplier: float,
) -> None:
    frame_delay = max(0.05, 1.0 / max(0.2, speed_multiplier))

    for payload in simulator.iter_attack(
        attack=attack,
        duration_seconds=duration_seconds,
        speed_multiplier=speed_multiplier,
        mode=mode,
        overrides=decoy_overrides if mode == "decoy" else None,
    ):
        if mode == "real":
            status = recorder.get_status()
            payload["attacker_profile"] = genome.classify(status["behavioral_features"])
            payload["patches_deployed"] = len(store.get_mitigation_rules())
        else:
            payload["active_overrides"] = decoy_overrides

        await websocket.send_json(payload)
        await asyncio.sleep(frame_delay)


@app.websocket("/ws/simulation")
async def ws_simulation(websocket: WebSocket) -> None:
    await websocket.accept()

    params = websocket.query_params
    attack_id = int(params.get("attack_id", "0"))
    speed = float(params.get("speed", "1.0"))
    duration = int(params.get("duration", "120"))

    attack = store.get_attack(attack_id)
    if not attack:
        attack = store.get_attack_library(limit=1)[0]

    try:
        await _stream_to_websocket(websocket, attack, "real", duration, speed)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/decoy")
async def ws_decoy(websocket: WebSocket) -> None:
    await websocket.accept()

    params = websocket.query_params
    attack_id = int(params.get("attack_id", "0"))
    speed = float(params.get("speed", "1.0"))
    duration = int(params.get("duration", "180"))

    attack = store.get_attack(attack_id)
    if not attack:
        attack = store.get_attack_library(limit=1)[0]

    try:
        await _stream_to_websocket(websocket, attack, "decoy", duration, speed)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/real")
async def ws_real(websocket: WebSocket) -> None:
    await websocket.accept()

    params = websocket.query_params
    attack_id = int(params.get("attack_id", "0"))
    speed = float(params.get("speed", "1.0"))
    duration = int(params.get("duration", "180"))

    attack = store.get_attack(attack_id)
    if not attack:
        attack = store.get_attack_library(limit=1)[0]

    try:
        await _stream_to_websocket(websocket, attack, "real", duration, speed)
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
