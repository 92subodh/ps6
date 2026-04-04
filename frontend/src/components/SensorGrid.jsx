function getBlindspotColor(score) {
  if (score < 3) {
    return 'border-emerald-300/70 bg-emerald-200/10';
  }
  if (score < 5) {
    return 'border-yellow-300/70 bg-yellow-200/10';
  }
  if (score < 7) {
    return 'border-orange-300/70 bg-orange-200/10';
  }
  return 'border-red-300/70 bg-red-200/15';
}

function formatValue(value) {
  if (typeof value !== 'number') {
    return '--';
  }
  return value.toFixed(3);
}

function SensorGrid({ sensorReadings = {}, blindspotScores = {}, flashingSensors = [], compact = false }) {
  const entries = Object.entries(sensorReadings).sort((a, b) => a[0].localeCompare(b[0]));
  const flashingSet = new Set(flashingSensors || []);

  if (!entries.length) {
    return (
      <div className="rounded-xl border border-white/20 bg-black/25 p-4 text-sm text-slate-300">
        Waiting for sensor stream...
      </div>
    );
  }

  return (
    <div
      className={
        'grid gap-2 ' +
        (compact
          ? 'grid-cols-2 md:grid-cols-3 xl:grid-cols-4'
          : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6')
      }
    >
      {entries.map(([sensorName, value], index) => {
        const score = Number(blindspotScores[sensorName] || 0);
        const colorClass = getBlindspotColor(score);
        const flashing = flashingSet.has(sensorName);

        return (
          <article
            key={sensorName}
            className={
              'stagger-entry rounded-lg border p-2 shadow-sm transition ' +
              colorClass +
              ' ' +
              (flashing ? 'alert-pulse' : '')
            }
            style={{ animationDelay: String((index % 18) * 16) + 'ms' }}
          >
            <p className="mono truncate text-xs tracking-wide text-slate-200">{sensorName}</p>
            <p className="mt-1 text-lg font-semibold text-white">{formatValue(value)}</p>
            <p className="mono mt-1 text-[11px] uppercase tracking-wider text-slate-300">
              BS {score.toFixed(2)}
            </p>
          </article>
        );
      })}
    </div>
  );
}

export default SensorGrid;
