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
