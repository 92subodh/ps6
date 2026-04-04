# Person 3 Setup Guide (Backend + Frontend + MIRROR)

This document covers the implementation added for:
- Layer 5 FastAPI backend
- Layer 5 React dashboard
- Project MIRROR components

## 1) Backend setup

From repo root:

```powershell
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

For highest NLP parsing quality, install spaCy English model once:

```powershell
python -m spacy download en_core_web_sm
```

If the model is absent, parser automatically falls back to spaCy blank tokenizer or regex mode.

Health check:

```powershell
curl http://localhost:8000/health
```

Primary endpoints:
- GET /attacks
- GET /attacks/{id}
- POST /simulate
- GET /blindspot-scores
- GET /kill-chains
- GET /shap/{attack_id}
- POST /what-if
- POST /apply-fix/{attack_id}

Explainability details:
- `/shap/{attack_id}` now uses model-backed Tree SHAP when available
- `/lime/{attack_id}` now uses LIME local explanations when available
- Both gracefully fall back to deterministic heuristic mode if optional packages are unavailable

MIRROR endpoints:
- POST /attacker/probe
- GET /mirror/status
- GET /mirror/profile

WebSockets:
- ws://localhost:8000/ws/simulation
- ws://localhost:8000/ws/decoy
- ws://localhost:8000/ws/real

## 2) Frontend setup

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs on:
- http://localhost:3000

If needed, override backend URL:

```powershell
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

## 3) Dashboard screens

Implemented routes:
- /command-center
- /attack-theater
- /vulnerability-heatmap
- /mitigation-engine
- /mirror

## 4) MIRROR demo flow

1. Open /mirror
2. Enter attacker commands in left panel (for example: set Feature_7 to 0.95)
3. Probe is intercepted and redirected to decoy endpoint
4. Blue team panel updates with recorder logs, profile classification, and patch count
5. Click "Reveal MIRROR" to show decoy vs real-state reveal

## 5) Data assumptions

The backend uses local JSON artifacts in data/synthetic.
If those files are absent, the service creates synthetic fallback attack profiles so the UI remains runnable.

## 6) Submission validation script

With backend running, execute:

```powershell
python validate_person3.py
```

The script verifies:
- Core REST endpoints
- Simulation/decoy/real WebSocket streams
- Persistence artifacts:
	- backend/generated/mitigation_rules.json
	- mirror/output/attacker_session.json

## 7) Restart persistence check

1. Trigger one fix and one attacker probe:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/apply-fix/0" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/attacker/probe" -Method Post -ContentType "application/json" -Body '{"query_type":"probe","sensors_queried":["Feature_7"],"command_sent":"set Feature_7 to 0.95"}'
```

2. Restart backend server.
3. Check status:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/mirror/status" -Method Get
```

Expected: prior actions remain visible in recent_actions and persisted files remain populated.
