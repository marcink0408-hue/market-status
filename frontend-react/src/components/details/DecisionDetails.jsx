import { normalizeDecision } from '../../utils/market';

const fmt = (value) => value == null || value === '' || !Number.isFinite(Number(value))
  ? '—' : Number(value).toLocaleString('pl-PL', { maximumFractionDigits: 5 });

export default function DecisionDetails({ instrument }) {
  const decision = normalizeDecision(instrument.decision);
  const color = decision === 'LONG' ? 'text-green-400' : decision === 'SHORT' ? 'text-red-400' : 'text-slate-300';
  const background = decision === 'LONG'
    ? 'from-green-950/60 border-green-500/40'
    : decision === 'SHORT' ? 'from-red-950/60 border-red-500/40' : 'from-panel border-border';
  const levelsTimeframe = instrument.levels_timeframe || '4H';

  return (
    <section className={`border rounded-2xl bg-gradient-to-r to-panel p-5 md:p-6 ${background}`}>
      <div className="grid lg:grid-cols-[1fr_auto] gap-6 items-center">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">Główny sygnał · {instrument.main_signal_timeframe || '4H'}</p>
          <div className={`text-4xl md:text-5xl font-black mt-2 ${color}`}>
            {decision === 'LONG' ? '↑ LONG' : decision === 'SHORT' ? '↓ SHORT' : '— BRAK'}
          </div>
          <p className="text-sm text-muted mt-3">
            {decision === 'BRAK' ? 'Brak potwierdzonego setupu na 4H.' : `Kierunek z 4H · poziomy końcowe z ${levelsTimeframe}`}
          </p>
          <p className="text-xs text-muted mt-1">Ocena punktowa modelu, nie prawdopodobieństwo zysku.</p>
        </div>
        <div className={`text-left lg:text-right ${color}`}>
          <span className="text-xs uppercase tracking-widest text-muted">Ocena sygnału</span>
          <div className="text-6xl md:text-7xl leading-none font-black mt-1">
            {instrument.confidence ?? '—'}<span className="text-2xl text-muted">/100</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
        {[
          ['Wejście', instrument.entry, 'text-text'],
          ['Stop Loss', instrument.stop, 'text-red-400'],
          ['Take Profit', instrument.target, 'text-green-400'],
        ].map(([label, value, className]) => (
          <div key={label} className="border border-border rounded-lg bg-bg/60 p-3">
            <div className="text-xs text-muted">{label} <span className="text-blue-300">({levelsTimeframe})</span></div>
            <div className={`font-black text-lg mt-1 ${className}`}>{fmt(value)}</div>
          </div>
        ))}
        <div className="border border-border rounded-lg bg-bg/60 p-3">
          <div className="text-xs text-muted">Zysk / ryzyko</div>
          <div className="font-black text-lg mt-1">{instrument.rr == null ? '—' : `1:${fmt(instrument.rr)}`}</div>
        </div>
      </div>
      {instrument.levels_basis && <p className="text-xs text-muted mt-3">{instrument.levels_basis}</p>}
    </section>
  );
}
