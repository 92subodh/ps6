# Person 3 Requirement Traceability (From GenTwin_Build_Spec)

This sheet maps Person 3 PDF requirements to implementation status and evidence in the repository.

## Layer 5 Backend

| ID | Requirement (PDF scope) | Status | Evidence |
|---|---|---|---|
| L5-BE-01 | Attack library API for ranked attacks | Complete | GET /attacks in backend/main.py |
| L5-BE-02 | Attack detail API | Complete | GET /attacks/{attack_id} in backend/main.py |
| L5-BE-03 | Simulation API with attack selection | Complete | POST /simulate in backend/main.py + backend/simulation.py |
| L5-BE-04 | Blindspot score API | Complete | GET /blindspot-scores in backend/main.py + backend/data_store.py |
| L5-BE-05 | Kill-chain API | Complete | GET /kill-chains in backend/main.py + backend/data_store.py |
| L5-BE-06 | Explainability API for SHAP | Complete (model-backed with fallback) | GET /shap/{attack_id} in backend/main.py + backend/data_store.py |
| L5-BE-07 | What-if natural language API | Complete (spaCy parser with fallback) | POST /what-if in backend/main.py + backend/query_parser.py |
| L5-BE-08 | Apply-fix API + rule persistence | Complete | POST /apply-fix/{attack_id} in backend/main.py + backend/generated/mitigation_rules.json |
| L5-BE-09 | Real-time simulation WebSocket | Complete | /ws/simulation in backend/main.py |
| L5-BE-10 | Decoy and real WebSocket channels | Complete | /ws/decoy and /ws/real in backend/main.py |

## Layer 5 Frontend

| ID | Requirement (PDF scope) | Status | Evidence |
|---|---|---|---|
| L5-FE-01 | Command Center screen | Complete | frontend/src/pages/CommandCenter.jsx |
| L5-FE-02 | Attack Theater screen | Complete | frontend/src/pages/AttackTheater.jsx |
| L5-FE-03 | Vulnerability Heatmap screen | Complete | frontend/src/pages/VulnerabilityHeatmap.jsx |
| L5-FE-04 | Mitigation Engine screen | Complete | frontend/src/pages/MitigationEngine.jsx |
| L5-FE-05 | Global what-if input and routing | Complete | frontend/src/components/Navbar.jsx + frontend/src/App.jsx |
| L5-FE-06 | Demo mode speed toggle | Complete | frontend/src/App.jsx + page websocket speed usage |

## Project MIRROR

| ID | Requirement (PDF scope) | Status | Evidence |
|---|---|---|---|
| MIR-01 | Probe interception endpoint | Complete | POST /attacker/probe in backend/main.py |
| MIR-02 | Action recorder for attacker behavior | Complete | mirror/recorder.py |
| MIR-03 | Attacker archetype/genome classification | Complete | mirror/profile.py |
| MIR-04 | MIRROR status/profile APIs | Complete | GET /mirror/status and GET /mirror/profile in backend/main.py |
| MIR-05 | Dual decoy-vs-real UI with reveal flow | Complete | frontend/src/pages/MirrorPage.jsx |
| MIR-06 | Recorder persistence across restart | Complete | mirror/recorder.py loads mirror/output/attacker_session.json |

## Validation Evidence

| Check | Status | Evidence |
|---|---|---|
| Runtime health and attack APIs | Complete | Manual smoke run on /health and /attacks |
| Backend/WebSocket contract checks | Complete | validate_person3.py |
| Persistence artifact checks | Complete | validate_person3.py checks mitigation and mirror output files |

## Known Partial Items (Beyond Submission Baseline)

1. Explainability pipeline is model-backed and uses SHAP/LIME when available, with deterministic fallback mode for degraded environments.
2. What-if parser uses spaCy (en_core_web_sm when installed) with blank/regex fallback.
3. Frontend bundle can still be optimized further for production deployment.
