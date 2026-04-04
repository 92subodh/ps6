import { NavLink } from 'react-router-dom';

const navItems = [
  { label: 'Command Center', to: '/command-center' },
  { label: 'Attack Theater', to: '/attack-theater' },
  { label: 'Vulnerability Heatmap', to: '/vulnerability-heatmap' },
  { label: 'AI Mitigation', to: '/mitigation-engine' },
  { label: 'MIRROR', to: '/mirror' },
];

function Navbar({
  demoMode,
  setDemoMode,
  whatIfQuery,
  setWhatIfQuery,
  onSubmitWhatIf,
  whatIfError,
  isSubmittingWhatIf,
}) {
  return (
    <header className="mx-auto mt-5 w-[95%] max-w-[1500px] rounded-2xl border border-white/20 bg-black/20 p-4 shadow-soft">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="mono text-xs uppercase tracking-[0.3em] text-mint">GenTwin Layer 5</p>
          <h1 className="text-2xl font-bold tracking-tight text-cloud">Operational Cyber Twin</h1>
        </div>

        <button
          type="button"
          onClick={() => setDemoMode(!demoMode)}
          className={
            'mono rounded-lg border px-3 py-2 text-xs uppercase tracking-[0.22em] transition ' +
            (demoMode
              ? 'border-amber-300/80 bg-amber-200/20 text-amber-100'
              : 'border-mint/60 bg-mint/10 text-mint')
          }
        >
          Demo Mode: {demoMode ? '3x Live' : 'Normal'}
        </button>
      </div>

      <nav className="mb-3 flex flex-wrap gap-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              'rounded-lg border px-3 py-2 text-sm transition ' +
              (isActive
                ? 'border-mint bg-mint/20 text-cloud'
                : 'border-white/15 bg-white/5 text-slate-200 hover:border-white/35 hover:bg-white/10')
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="grid gap-2 md:grid-cols-[1fr_auto]">
        <textarea
          value={whatIfQuery}
          onChange={(event) => setWhatIfQuery(event.target.value)}
          placeholder="What-if engine: describe a scenario, for example 'What if P2 has a drift attack during high flow?'"
          rows={2}
          className="w-full resize-none rounded-xl border border-white/20 bg-black/25 p-3 text-sm text-slate-100 placeholder:text-slate-400 focus:border-mint/70 focus:outline-none"
        />
        <button
          type="button"
          disabled={isSubmittingWhatIf}
          onClick={onSubmitWhatIf}
          className="rounded-xl border border-amber-200/80 bg-gradient-to-r from-amber-300/70 to-orange-400/70 px-4 py-2 font-semibold text-slate-900 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmittingWhatIf ? 'Running...' : 'Run What-If'}
        </button>
      </div>

      {whatIfError ? <p className="mt-2 text-sm text-red-200">{whatIfError}</p> : null}
    </header>
  );
}

export default Navbar;
