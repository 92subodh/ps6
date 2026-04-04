import { useEffect, useMemo, useState } from 'react';
import { api, getWsBaseUrl } from '../api/client';
import SensorGrid from '../components/SensorGrid';
import StageOverview from '../components/StageOverview';

function stageFromIndex(index) {
  if (index < 9) return 'P1';
  if (index < 17) return 'P2';
  if (index < 26) return 'P3';
  if (index < 34) return 'P4';
  if (index < 43) return 'P5';
  return 'P6';
}

function stageTone(score) {
  if (score < 3) return '#52d1a9';
  if (score < 5) return '#f1d075';
  if (score < 7) return '#f2a85a';
  return '#eb6558';
}

function CommandCenter({ demoMode }) {
  const [blindspotScores, setBlindspotScores] = useState({});
  const [sensorReadings, setSensorReadings] = useState({});
  const [connectionLabel, setConnectionLabel] = useState('Connecting...');

  useEffect(() => {
    let cancelled = false;

    const fetchBlindspots = async () => {
      try {
        const response = await api.get('/blindspot-scores');
        if (!cancelled) {
          setBlindspotScores(response.data || {});
        }
      } catch (error) {
        if (!cancelled) {
          setConnectionLabel('Backend unavailable for blindspot scores.');
        }
      }
    };

    fetchBlindspots();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const wsUrl =
      getWsBaseUrl() +
      '/ws/real?attack_id=0&speed=' +
      (demoMode ? '3' : '1') +
      '&duration=720';

    const socket = new WebSocket(wsUrl);
    socket.onopen = () => {
      setConnectionLabel('Live stream active');
    };
    socket.onclose = () => {
      setConnectionLabel('Live stream closed');
    };
    socket.onerror = () => {
      setConnectionLabel('WebSocket error');
    };
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setSensorReadings(payload.sensor_readings || {});
      } catch (error) {
        setConnectionLabel('Malformed stream payload');
      }
    };

    return () => {
      socket.close();
    };
  }, [demoMode]);

  const mergedReadings = useMemo(() => {
    if (Object.keys(sensorReadings).length > 0) {
      return sensorReadings;
    }

    const fallback = {};
    Object.entries(blindspotScores).forEach(([sensor, score], idx) => {
      fallback[sensor] = Number(score) * (1 + ((idx % 7) - 3) * 0.01);
    });
    return fallback;
  }, [sensorReadings, blindspotScores]);

  const stageSummary = useMemo(() => {
    const stageScores = {
      P1: [],
      P2: [],
      P3: [],
      P4: [],
      P5: [],
      P6: [],
    };

    Object.values(blindspotScores).forEach((score, index) => {
      const stage = stageFromIndex(index);
      stageScores[stage].push(Number(score));
    });

    return Object.entries(stageScores).map(([stage, values]) => {
      const average = values.length
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : 0;
      return {
        stage,
        average,
      };
    });
  }, [blindspotScores]);

  const avgBlindspot =
    Object.keys(blindspotScores).length > 0
      ? (
          Object.values(blindspotScores).reduce((sum, value) => sum + Number(value), 0) /
          Object.keys(blindspotScores).length
        ).toFixed(2)
      : '--';

  return (
    <section className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="glass-panel rounded-xl p-4">
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">Blindspot Average</p>
          <h2 className="text-3xl font-bold text-cloud">{avgBlindspot}</h2>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">Sensors Online</p>
          <h2 className="text-3xl font-bold text-cloud">{Object.keys(mergedReadings).length || 51}</h2>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">Connection</p>
          <h2 className="text-xl font-semibold text-cloud">{connectionLabel}</h2>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="glass-panel rounded-xl p-4">
          <h3 className="mb-2 text-lg font-semibold">Live Sensor Grid</h3>
          <SensorGrid sensorReadings={mergedReadings} blindspotScores={blindspotScores} />
        </div>

        <div className="space-y-4">
          <StageOverview blindspotScores={blindspotScores} />

          <div className="glass-panel rounded-xl p-4">
            <h3 className="text-lg font-semibold text-cloud">Plant Diagram Overlay</h3>
            <p className="mono mb-2 text-xs uppercase tracking-[0.18em] text-slate-300">
              Stage-color reflects blindspot severity
            </p>
            <svg viewBox="0 0 520 190" className="w-full rounded-lg bg-black/20 p-2">
              {stageSummary.map((row, index) => {
                const x = 10 + index * 84;
                return (
                  <g key={row.stage}>
                    <rect
                      x={x}
                      y={50}
                      width={72}
                      height={70}
                      rx={10}
                      fill={stageTone(row.average)}
                      fillOpacity={0.65}
                      stroke="rgba(255,255,255,0.6)"
                    />
                    <text x={x + 36} y={88} textAnchor="middle" fill="#ffffff" fontSize="18">
                      {row.stage}
                    </text>
                    <text
                      x={x + 36}
                      y={110}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="11"
                      className="mono"
                    >
                      {row.average.toFixed(2)}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}

export default CommandCenter;
