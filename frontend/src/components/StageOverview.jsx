function stageForIndex(index) {
  if (index < 9) return 'P1';
  if (index < 17) return 'P2';
  if (index < 26) return 'P3';
  if (index < 34) return 'P4';
  if (index < 43) return 'P5';
  return 'P6';
}

function stageTone(score) {
  if (score < 3) return 'bg-emerald-400';
  if (score < 5) return 'bg-yellow-400';
  if (score < 7) return 'bg-orange-400';
  return 'bg-red-400';
}

function StageOverview({ blindspotScores = {} }) {
  const entries = Object.entries(blindspotScores);
  const stageBuckets = {
    P1: [],
    P2: [],
    P3: [],
    P4: [],
    P5: [],
    P6: [],
  };

  entries.forEach(([, score], index) => {
    const stage = stageForIndex(index);
    stageBuckets[stage].push(Number(score));
  });

  const stageRows = Object.entries(stageBuckets).map(([stage, scores]) => {
    const average = scores.length
      ? scores.reduce((sum, value) => sum + value, 0) / scores.length
      : 0;
    return {
      stage,
      average,
      tone: stageTone(average),
    };
  });

  return (
    <div className="glass-panel rounded-xl p-4">
      <h3 className="text-lg font-semibold text-cloud">Plant Stage Risk Overlay</h3>
      <p className="mono mb-3 text-xs uppercase tracking-[0.18em] text-slate-300">
        P1 through P6 aggregate blindspot score
      </p>

      <div className="space-y-2">
        {stageRows.map((row) => (
          <div key={row.stage} className="rounded-lg border border-white/15 bg-black/20 p-2">
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-medium">{row.stage}</span>
              <span className="mono text-slate-200">{row.average.toFixed(2)}</span>
            </div>
            <div className="h-2 rounded bg-slate-800/80">
              <div
                className={'h-2 rounded ' + row.tone}
                style={{ width: Math.min(100, row.average * 12) + '%' }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default StageOverview;
