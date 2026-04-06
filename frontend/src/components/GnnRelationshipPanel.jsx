const STAGE_NODES = [
  { id: 0, stage: 'P1', sensor: 'Feature_0', x: 72, y: 160 },
  { id: 1, stage: 'P2', sensor: 'Feature_9', x: 190, y: 88 },
  { id: 2, stage: 'P3', sensor: 'Feature_17', x: 308, y: 160 },
  { id: 3, stage: 'P4', sensor: 'Feature_26', x: 426, y: 88 },
  { id: 4, stage: 'P5', sensor: 'Feature_34', x: 544, y: 160 },
  { id: 5, stage: 'P6', sensor: 'Feature_43', x: 662, y: 88 },
];

function formatLatency(value) {
  if (typeof value !== 'number') {
    return '--';
  }
  return value.toFixed(1) + 's';
}

function statusTone(score) {
  if (score >= 80) return 'text-emerald-200';
  if (score >= 60) return 'text-yellow-200';
  if (score >= 40) return 'text-orange-200';
  return 'text-red-200';
}

function baselineLabel(rate) {
  if (typeof rate !== 'number') {
    return 'Unknown';
  }
  if (rate < 30) {
    return 'Likely miss (<30% detection)';
  }
  if (rate < 70) {
    return 'Partial coverage';
  }
  return 'Strong coverage';
}

function edgeKey(fromId, toId) {
  return String(fromId) + '-' + String(toId);
}

function GnnRelationshipPanel({ relationshipSnapshot, streamStatus }) {
  const edgeMap = new Map(
    (relationshipSnapshot?.edgeStates || []).map((edge) => [edgeKey(edge.fromId, edge.toId), edge])
  );

  const integrityScore = Number(relationshipSnapshot?.integrityScore || 100);
  const edgesBroken = Number(relationshipSnapshot?.edgesBroken || 0);
  const totalEdges = Number(relationshipSnapshot?.totalEdges || 0);
  const gnnLatency = relationshipSnapshot?.gnnAlertLatencySec;
  const baselineRate = relationshipSnapshot?.baselineDetectionRate;

  return (
    <div className="glass-panel rounded-xl p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold">GNN Relationship Panel</h3>
          <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">
            Live graph integrity over process-stage sensor dependencies
          </p>
        </div>
        <p className="mono text-xs uppercase tracking-[0.2em] text-slate-300">
          Stream: {streamStatus}
        </p>
      </div>

      <div className="mb-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-white/15 bg-black/20 p-2">
          <p className="mono text-[11px] uppercase tracking-[0.16em] text-slate-300">Graph Integrity</p>
          <p className={'text-xl font-bold ' + statusTone(integrityScore)}>{integrityScore.toFixed(1)}%</p>
        </div>
        <div className="rounded-lg border border-white/15 bg-black/20 p-2">
          <p className="mono text-[11px] uppercase tracking-[0.16em] text-slate-300">Broken Edges</p>
          <p className="text-xl font-bold text-red-200">
            {edgesBroken}/{totalEdges}
          </p>
        </div>
        <div className="rounded-lg border border-white/15 bg-black/20 p-2">
          <p className="mono text-[11px] uppercase tracking-[0.16em] text-slate-300">GNN Alert Latency</p>
          <p className="text-xl font-bold text-cyan-100">{formatLatency(gnnLatency)}</p>
        </div>
        <div className="rounded-lg border border-white/15 bg-black/20 p-2">
          <p className="mono text-[11px] uppercase tracking-[0.16em] text-slate-300">Baseline LSTM</p>
          <p className="text-sm font-semibold text-slate-100">{baselineLabel(baselineRate)}</p>
          <p className="mono text-[11px] text-slate-300">
            {typeof baselineRate === 'number' ? baselineRate.toFixed(1) + '% detection' : '--'}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-white/15 bg-black/20 p-2">
        <svg viewBox="0 0 734 240" className="w-full">
          {[
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
            [4, 5],
            [0, 2],
            [2, 4],
          ].map(([fromId, toId]) => {
            const fromNode = STAGE_NODES[fromId];
            const toNode = STAGE_NODES[toId];
            const edge = edgeMap.get(edgeKey(fromId, toId));
            const broken = Boolean(edge?.broken);

            return (
              <line
                key={edgeKey(fromId, toId)}
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                stroke={broken ? '#f87171' : '#6ee7b7'}
                strokeWidth={broken ? 3.6 : 2.2}
                strokeDasharray={broken ? '7 5' : 'none'}
                opacity={0.95}
              />
            );
          })}

          {STAGE_NODES.map((node) => {
            const hasBrokenEdge = Array.from(edgeMap.values()).some(
              (edge) => edge.broken && (edge.fromId === node.id || edge.toId === node.id)
            );

            return (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={28}
                  fill={hasBrokenEdge ? 'rgba(239,68,68,0.35)' : 'rgba(34,197,94,0.28)'}
                  stroke={hasBrokenEdge ? '#fca5a5' : '#9ae6b4'}
                  strokeWidth={2}
                />
                <text x={node.x} y={node.y - 4} textAnchor="middle" fill="#f8fafc" fontSize="14">
                  {node.stage}
                </text>
                <text
                  x={node.x}
                  y={node.y + 13}
                  textAnchor="middle"
                  fill="#cbd5e1"
                  fontSize="10"
                  className="mono"
                >
                  {node.sensor}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default GnnRelationshipPanel;
