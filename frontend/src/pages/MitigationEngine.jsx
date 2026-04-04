import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';

function MitigationEngine() {
  const [gaps, setGaps] = useState([]);
  const [isApplying, setIsApplying] = useState({});
  const [stats, setStats] = useState({
    beforeRate: 0,
    afterRate: 0,
    fixesApplied: 0,
  });

  useEffect(() => {
    let cancelled = false;

    const loadGaps = async () => {
      try {
        const response = await api.get('/gaps?limit=40');
        if (cancelled) {
          return;
        }

        const loadedGaps = response?.data?.gaps || [];
        setGaps(loadedGaps);

        const beforeRate =
          loadedGaps.length > 0
            ? loadedGaps.reduce((sum, item) => sum + Number(item.detection_rate || 0), 0) /
              loadedGaps.length
            : 0;

        setStats({
          beforeRate,
          afterRate: beforeRate,
          fixesApplied: 0,
        });
      } catch (error) {
        if (!cancelled) {
          setGaps([]);
        }
      }
    };

    loadGaps();

    return () => {
      cancelled = true;
    };
  }, []);

  const improvement = useMemo(
    () => Math.max(0, stats.afterRate - stats.beforeRate),
    [stats.afterRate, stats.beforeRate]
  );

  const applyFix = async (attackId) => {
    setIsApplying((current) => ({ ...current, [attackId]: true }));
    try {
      const response = await api.post('/apply-fix/' + String(attackId));
      const payload = response?.data;

      setGaps((current) =>
        current.map((item) => {
          if (Number(item.attack_id) !== Number(attackId)) {
            return item;
          }

          return {
            ...item,
            detection_rate: Number(payload.after_detection_rate || item.detection_rate),
            mitigation_applied: true,
          };
        })
      );

      setStats((current) => {
        const nextFixes = current.fixesApplied + 1;
        const totalDelta = Number(payload.after_detection_rate || 0) - Number(payload.before_detection_rate || 0);
        return {
          ...current,
          fixesApplied: nextFixes,
          afterRate: current.afterRate + totalDelta / Math.max(1, gaps.length),
        };
      });
    } catch (error) {
      // Keep UX simple: row state remains unchanged on failure.
    } finally {
      setIsApplying((current) => ({ ...current, [attackId]: false }));
    }
  };

  return (
    <section className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="glass-panel rounded-xl p-4">
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">Before Detection</p>
          <h2 className="text-3xl font-bold text-cloud">{stats.beforeRate.toFixed(2)}%</h2>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">After Detection</p>
          <h2 className="text-3xl font-bold text-cloud">{stats.afterRate.toFixed(2)}%</h2>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">Improvement</p>
          <h2 className="text-3xl font-bold text-mint">+{improvement.toFixed(2)}%</h2>
          <p className="text-sm text-slate-200">Fixes applied: {stats.fixesApplied}</p>
        </div>
      </div>

      <div className="glass-panel rounded-xl p-4">
        <h3 className="mb-2 text-lg font-semibold">AI Mitigation Rule Deployment</h3>
        <div className="space-y-3">
          {gaps.map((gap) => {
            const attackId = Number(gap.attack_id);
            const limeRule = gap.lime_rule || {};

            return (
              <article
                key={attackId}
                className="rounded-xl border border-white/15 bg-black/20 p-3"
              >
                <div className="mb-2 grid gap-2 md:grid-cols-[1fr_auto]">
                  <div>
                    <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">
                      Attack #{attackId} | {gap.gap_type}
                    </p>
                    <h4 className="text-base font-semibold text-cloud">
                      Impact {Number(gap.impact_score).toFixed(2)} | Detection {Number(gap.detection_rate).toFixed(2)}%
                    </h4>
                  </div>
                  <button
                    type="button"
                    onClick={() => applyFix(attackId)}
                    disabled={Boolean(isApplying[attackId])}
                    className={
                      'rounded-lg border px-4 py-2 text-sm font-semibold transition ' +
                      (gap.mitigation_applied
                        ? 'border-emerald-300/70 bg-emerald-200/20 text-emerald-100'
                        : 'border-amber-200/70 bg-amber-200/20 text-amber-100 hover:brightness-110')
                    }
                  >
                    {isApplying[attackId]
                      ? 'Applying...'
                      : gap.mitigation_applied
                      ? 'Fix Applied'
                      : 'Apply Fix'}
                  </button>
                </div>

                <div className="rounded-lg border border-white/10 bg-black/15 p-2 text-sm text-slate-200">
                  <p className="font-medium">LIME Rule</p>
                  <p>{limeRule.condition_text || 'Rule unavailable for this attack.'}</p>
                </div>
              </article>
            );
          })}

          {gaps.length === 0 ? (
            <p className="text-sm text-slate-300">No gaps available. Ensure backend artifacts are loaded.</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export default MitigationEngine;
