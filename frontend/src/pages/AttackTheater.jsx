import { useEffect, useMemo, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import { useSearchParams } from 'react-router-dom';
import { api, getWsBaseUrl } from '../api/client';
import GnnRelationshipPanel from '../components/GnnRelationshipPanel';
import SensorGrid from '../components/SensorGrid';

const STAGE_REP_SENSORS = ['Feature_0', 'Feature_9', 'Feature_17', 'Feature_26', 'Feature_34', 'Feature_43'];
const RELATIONSHIP_EDGES = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [4, 5],
  [0, 2],
  [2, 4],
];
const BASELINE_SAMPLE_COUNT = 5;

function edgeKey(fromId, toId) {
  return String(fromId) + '-' + String(toId);
}

function safeNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function extractEdgeMap(sensorReadings) {
  const nodeValues = STAGE_REP_SENSORS.map((sensorName) => safeNumber(sensorReadings[sensorName]));
  const map = {};

  RELATIONSHIP_EDGES.forEach(([fromId, toId]) => {
    map[edgeKey(fromId, toId)] = nodeValues[toId] - nodeValues[fromId];
  });

  return map;
}

function meanEdgeMap(edgeMaps) {
  if (!edgeMaps.length) {
    return {};
  }

  const aggregate = {};
  edgeMaps.forEach((item) => {
    Object.entries(item).forEach(([key, value]) => {
      aggregate[key] = (aggregate[key] || 0) + Number(value);
    });
  });

  const out = {};
  Object.entries(aggregate).forEach(([key, value]) => {
    out[key] = value / edgeMaps.length;
  });

  return out;
}

function AttackTheater({ demoMode }) {
  const [searchParams] = useSearchParams();
  const [attacks, setAttacks] = useState([]);
  const [blindspotScores, setBlindspotScores] = useState({});
  const [selectedAttackId, setSelectedAttackId] = useState(0);
  const [sensorReadings, setSensorReadings] = useState({});
  const [timeline, setTimeline] = useState({ x: [], lines: {} });
  const [flashingSensors, setFlashingSensors] = useState([]);
  const [streamStatus, setStreamStatus] = useState('idle');
  const [latestTimestep, setLatestTimestep] = useState(0);
  const [relationshipSnapshot, setRelationshipSnapshot] = useState({
    integrityScore: 100,
    edgesBroken: 0,
    totalEdges: RELATIONSHIP_EDGES.length,
    gnnAlertLatencySec: null,
    baselineDetectionRate: null,
    edgeStates: RELATIONSHIP_EDGES.map(([fromId, toId]) => ({
      fromId,
      toId,
      broken: false,
      deviation: 0,
    })),
  });

  const socketRef = useRef(null);
  const previousReadingsRef = useRef({});
  const relationshipBaselineSamplesRef = useRef([]);
  const relationshipBaselineRef = useRef({});
  const gnnAlertFrameRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      try {
        const [attacksResponse, blindspotResponse] = await Promise.all([
          api.get('/attacks?limit=300'),
          api.get('/blindspot-scores'),
        ]);

        if (cancelled) return;

        const loadedAttacks = attacksResponse.data || [];
        setAttacks(loadedAttacks);
        setBlindspotScores(blindspotResponse.data || {});

        const fromQuery = Number(searchParams.get('attackId'));
        if (!Number.isNaN(fromQuery) && loadedAttacks.some((item) => item.attack_id === fromQuery)) {
          setSelectedAttackId(fromQuery);
        } else if (loadedAttacks.length > 0) {
          setSelectedAttackId(loadedAttacks[0].attack_id);
        }
      } catch (error) {
        setStreamStatus('error_loading');
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  const selectedAttack = useMemo(
    () => attacks.find((item) => item.attack_id === Number(selectedAttackId)),
    [attacks, selectedAttackId]
  );

  const stopStream = () => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setStreamStatus('stopped');
  };

  const startStream = () => {
    if (!selectedAttack) {
      return;
    }

    stopStream();
    setTimeline({ x: [], lines: {} });
    previousReadingsRef.current = {};
    relationshipBaselineSamplesRef.current = [];
    relationshipBaselineRef.current = {};
    gnnAlertFrameRef.current = null;
    setLatestTimestep(0);
    setRelationshipSnapshot({
      integrityScore: 100,
      edgesBroken: 0,
      totalEdges: RELATIONSHIP_EDGES.length,
      gnnAlertLatencySec: null,
      baselineDetectionRate:
        selectedAttack && typeof selectedAttack.detection_rate === 'number'
          ? Number(selectedAttack.detection_rate)
          : null,
      edgeStates: RELATIONSHIP_EDGES.map(([fromId, toId]) => ({
        fromId,
        toId,
        broken: false,
        deviation: 0,
      })),
    });

    const speed = demoMode ? 3 : 1;
    const wsUrl =
      getWsBaseUrl() +
      '/ws/simulation?attack_id=' +
      String(selectedAttack.attack_id) +
      '&speed=' +
      String(speed) +
      '&duration=260';

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setStreamStatus('running');
    };

    socket.onclose = () => {
      setStreamStatus('closed');
    };

    socket.onerror = () => {
      setStreamStatus('stream_error');
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const nextReadings = payload.sensor_readings || {};
        const frameTimestep = Number(payload.timestep || 0);
        setLatestTimestep(frameTimestep);
        setSensorReadings(nextReadings);

        const tracked = Object.keys(nextReadings).slice(0, 6);
        setTimeline((current) => {
          const nextX = [...current.x, payload.timestep].slice(-120);
          const nextLines = { ...current.lines };

          tracked.forEach((sensorName) => {
            const values = nextLines[sensorName] ? [...nextLines[sensorName]] : [];
            values.push(Number(nextReadings[sensorName]));
            nextLines[sensorName] = values.slice(-120);
          });

          return {
            x: nextX,
            lines: nextLines,
          };
        });

        const previous = previousReadingsRef.current;
        const flashes = tracked.filter((sensorName) => {
          const prev = Number(previous[sensorName] || 0);
          const curr = Number(nextReadings[sensorName] || 0);
          const delta = Math.abs(curr - prev);
          return delta > Math.max(0.5, Math.abs(prev) * 0.08);
        });
        setFlashingSensors(flashes);
        previousReadingsRef.current = nextReadings;

        const edgeMap = extractEdgeMap(nextReadings);
        if (!Object.keys(relationshipBaselineRef.current).length) {
          relationshipBaselineSamplesRef.current.push(edgeMap);
          if (relationshipBaselineSamplesRef.current.length >= BASELINE_SAMPLE_COUNT) {
            relationshipBaselineRef.current = meanEdgeMap(relationshipBaselineSamplesRef.current);
          }
        }

        const baselineMap = relationshipBaselineRef.current;
        const sigma = Number(selectedAttack?.sigma || 1);
        const deviationThreshold = Math.max(0.26, 0.5 - (sigma * 0.06));

        let brokenCount = 0;
        let deviationTotal = 0;
        const edgeStates = RELATIONSHIP_EDGES.map(([fromId, toId]) => {
          const key = edgeKey(fromId, toId);
          const baselineValue = Number(baselineMap[key] || 0);
          const liveValue = Number(edgeMap[key] || 0);
          const deviation = Math.abs(liveValue - baselineValue) / Math.max(0.8, Math.abs(baselineValue));
          const broken = Object.keys(baselineMap).length > 0 && deviation > deviationThreshold;
          deviationTotal += deviation;
          if (broken) {
            brokenCount += 1;
          }

          return {
            fromId,
            toId,
            broken,
            deviation,
          };
        });

        if (brokenCount > 0 && gnnAlertFrameRef.current === null) {
          gnnAlertFrameRef.current = frameTimestep;
        }

        const avgDeviation = edgeStates.length ? deviationTotal / edgeStates.length : 0;
        const integrityScore = Math.max(
          0,
          100 - (brokenCount / RELATIONSHIP_EDGES.length) * 55 - Math.min(45, avgDeviation * 26)
        );

        setRelationshipSnapshot({
          integrityScore,
          edgesBroken: brokenCount,
          totalEdges: RELATIONSHIP_EDGES.length,
          gnnAlertLatencySec:
            typeof gnnAlertFrameRef.current === 'number' && gnnAlertFrameRef.current > 0
              ? gnnAlertFrameRef.current
              : null,
          baselineDetectionRate:
            selectedAttack && typeof selectedAttack.detection_rate === 'number'
              ? Number(selectedAttack.detection_rate)
              : null,
          edgeStates,
        });
      } catch (error) {
        setStreamStatus('payload_error');
      }
    };
  };

  const traces = Object.entries(timeline.lines).map(([sensorName, values]) => ({
    x: timeline.x.slice(-values.length),
    y: values,
    type: 'scatter',
    mode: 'lines',
    name: sensorName,
  }));

  return (
    <section className="space-y-4">
      <div className="glass-panel rounded-xl p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <select
            value={selectedAttackId}
            onChange={(event) => setSelectedAttackId(Number(event.target.value))}
            className="rounded-lg border border-white/20 bg-black/20 px-3 py-2 text-sm text-white"
          >
            {attacks.map((attack) => (
              <option key={attack.attack_id} value={attack.attack_id}>
                #{attack.attack_id} | {attack.attack_type} | {attack.target_stage} | Rank {attack.rank_score}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={startStream}
            className="rounded-lg border border-mint/70 bg-mint/15 px-4 py-2 font-semibold text-white"
          >
            Launch Attack
          </button>

          <button
            type="button"
            onClick={stopStream}
            className="rounded-lg border border-red-300/70 bg-red-300/20 px-4 py-2 font-semibold text-white"
          >
            Stop
          </button>
        </div>

        <p className="mono mt-2 text-xs uppercase tracking-[0.2em] text-slate-300">
          Stream status: {streamStatus}
        </p>

        {selectedAttack ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-md border border-white/15 bg-black/20 p-2 text-sm">
              ID: {selectedAttack.attack_id}
            </div>
            <div className="rounded-md border border-white/15 bg-black/20 p-2 text-sm">
              Type: {selectedAttack.attack_type}
            </div>
            <div className="rounded-md border border-white/15 bg-black/20 p-2 text-sm">
              Stage: {selectedAttack.target_stage}
            </div>
            <div className="rounded-md border border-white/15 bg-black/20 p-2 text-sm">
              Impact: {selectedAttack.impact_score}
            </div>
            <div className="rounded-md border border-white/15 bg-black/20 p-2 text-sm">
              Detection: {selectedAttack.detection_rate}%
            </div>
          </div>
        ) : null}
      </div>

      <GnnRelationshipPanel relationshipSnapshot={relationshipSnapshot} streamStatus={streamStatus} />

      <div className="glass-panel rounded-xl p-4">
        <h3 className="mb-2 text-lg font-semibold">Live Affected Sensor Timeline</h3>
        <Plot
          data={traces}
          layout={{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0.18)',
            font: { color: '#eef3f7' },
            margin: { t: 20, r: 20, b: 35, l: 45 },
            xaxis: { title: 'Timestep' },
            yaxis: { title: 'Value' },
            legend: { orientation: 'h' },
          }}
          style={{ width: '100%', height: '320px' }}
          useResizeHandler
          config={{ displaylogo: false }}
        />
      </div>

      <div className="glass-panel rounded-xl p-4">
        <h3 className="mb-2 text-lg font-semibold">Real-Time Sensor Deviation Grid</h3>
        <p className="mono mb-2 text-xs uppercase tracking-[0.2em] text-slate-300">
          Timestep: {latestTimestep || '--'}
        </p>
        <SensorGrid
          sensorReadings={sensorReadings}
          blindspotScores={blindspotScores}
          flashingSensors={flashingSensors}
        />
      </div>
    </section>
  );
}

export default AttackTheater;
