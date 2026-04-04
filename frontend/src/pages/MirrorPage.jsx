import { useEffect, useMemo, useState } from 'react';
import { api, getWsBaseUrl } from '../api/client';
import SensorGrid from '../components/SensorGrid';

function extractSensorsFromCommand(commandText) {
  const sensors = [];
  const pattern = /(Feature_\d+)/gi;
  let match = pattern.exec(commandText);
  while (match) {
    sensors.push(match[1]);
    match = pattern.exec(commandText);
  }
  return sensors;
}

function MirrorPage({ demoMode }) {
  const [decoyReadings, setDecoyReadings] = useState({});
  const [realReadings, setRealReadings] = useState({});
  const [mirrorStatus, setMirrorStatus] = useState(null);
  const [commandText, setCommandText] = useState('set Feature_7 to 0.95');
  const [commandResult, setCommandResult] = useState('');
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const speed = demoMode ? 3 : 1;

    const decoySocket = new WebSocket(
      getWsBaseUrl() + '/ws/decoy?attack_id=0&speed=' + String(speed) + '&duration=720'
    );
    const realSocket = new WebSocket(
      getWsBaseUrl() + '/ws/real?attack_id=0&speed=' + String(speed) + '&duration=720'
    );

    decoySocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setDecoyReadings(payload.sensor_readings || {});
      } catch (error) {
        // Ignore malformed payloads.
      }
    };

    realSocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setRealReadings(payload.sensor_readings || {});
      } catch (error) {
        // Ignore malformed payloads.
      }
    };

    return () => {
      decoySocket.close();
      realSocket.close();
    };
  }, [demoMode]);

  useEffect(() => {
    let cancelled = false;

    const pullStatus = async () => {
      try {
        const response = await api.get('/mirror/status');
        if (!cancelled) {
          setMirrorStatus(response.data);
        }
      } catch (error) {
        if (!cancelled) {
          setMirrorStatus(null);
        }
      }
    };

    pullStatus();
    const timer = setInterval(pullStatus, 3000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const submitCommand = async () => {
    try {
      const sensors = extractSensorsFromCommand(commandText);
      const response = await api.post('/attacker/probe', {
        query_type: 'probe',
        sensors_queried: sensors,
        command_sent: commandText,
      });

      setCommandResult('Probe intercepted and redirected to fake plant.');
      setMirrorStatus((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          attacker_profile: response.data.attacker_profile,
        };
      });
    } catch (error) {
      setCommandResult('Probe failed. Ensure backend API is running.');
    }
  };

  const renderedDecoy = useMemo(() => {
    if (revealed) {
      return realReadings;
    }
    return decoyReadings;
  }, [revealed, decoyReadings, realReadings]);

  return (
    <section className="space-y-4">
      <div className="glass-panel rounded-xl p-4">
        <h3 className="text-lg font-semibold">MIRROR Two-Screen Demo</h3>
        <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">
          Left: attacker decoy feed | Right: blue team real plant
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-xl border border-red-300/40 bg-red-950/20 p-3">
          <h4 className="mono text-xs uppercase tracking-[0.22em] text-red-200">Attacker Terminal</h4>
          <div className="mt-2 grid gap-2">
            <textarea
              value={commandText}
              onChange={(event) => setCommandText(event.target.value)}
              rows={2}
              className="w-full resize-none rounded-lg border border-red-200/35 bg-black/35 p-2 text-sm text-red-100"
            />
            <button
              type="button"
              onClick={submitCommand}
              className="rounded-lg border border-red-200/70 bg-red-300/25 px-3 py-2 font-semibold text-red-100"
            >
              Send Probe
            </button>
            {commandResult ? <p className="text-sm text-red-100">{commandResult}</p> : null}
          </div>

          <div className="mt-3">
            <SensorGrid sensorReadings={renderedDecoy} blindspotScores={{}} compact />
          </div>
        </div>

        <div className="flex items-center justify-center">
          <div className="rounded-full border border-white/30 bg-black/25 px-4 py-16 text-center">
            <p className="mono text-xs uppercase tracking-[0.3em] text-amber-200">Attacker Believes This Is Real</p>
          </div>
        </div>

        <div className="rounded-xl border border-cyan-300/40 bg-cyan-950/20 p-3">
          <h4 className="mono text-xs uppercase tracking-[0.22em] text-cyan-100">Mirror Control</h4>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <div className="rounded-lg border border-cyan-100/20 bg-black/20 p-2 text-sm text-cyan-100">
              Session: {mirrorStatus?.session_id || 'N/A'}
            </div>
            <div className="rounded-lg border border-cyan-100/20 bg-black/20 p-2 text-sm text-cyan-100">
              Patches Deployed: {mirrorStatus?.patches_deployed || 0}
            </div>
          </div>

          <div className="mt-3">
            <SensorGrid sensorReadings={realReadings} blindspotScores={{}} compact />
          </div>

          <div className="mt-3 rounded-lg border border-cyan-200/25 bg-black/25 p-2 text-sm">
            <p className="font-semibold text-cyan-100">Attacker Genome Profile</p>
            <p className="text-cyan-50">
              {mirrorStatus?.attacker_profile?.archetype || 'Waiting for actions'}
            </p>
            <p className="mono text-xs text-cyan-200">
              Confidence: {mirrorStatus?.attacker_profile?.confidence || '--'}
            </p>
          </div>

          <div className="mt-3 rounded-lg border border-white/15 bg-black/30 p-2 text-xs text-slate-200">
            <p className="mono uppercase tracking-[0.2em] text-slate-300">Recorder Log</p>
            <div className="mt-2 max-h-40 overflow-auto space-y-1">
              {(mirrorStatus?.recent_actions || []).slice(-12).map((item, idx) => (
                <p key={String(idx) + item.timestamp} className="mono text-[11px] text-slate-300">
                  {item.timestamp} | {item.type} | {(item.target_sensors || []).join(', ')}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="glass-panel rounded-xl p-4">
        <button
          type="button"
          onClick={() => setRevealed((current) => !current)}
          className="rounded-lg border border-amber-200/75 bg-amber-300/25 px-4 py-2 font-semibold text-amber-100"
        >
          {revealed ? 'Hide MIRROR' : 'Reveal MIRROR'}
        </button>

        {revealed ? (
          <p className="mt-2 text-sm text-amber-100">
            Attacker achieved nothing. Real plant untouched. Full strategy captured.
          </p>
        ) : null}
      </div>
    </section>
  );
}

export default MirrorPage;
