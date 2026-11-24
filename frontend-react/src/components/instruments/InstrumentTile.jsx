export default function InstrumentTile({ instrument, selected, onSelect }) {
  const direction = instrument.decision;
  const colors = direction === 'LONG'
    ? 'border-green-500/50 bg-green-950/30 hover:border-green-400'
    : direction === 'SHORT'
      ? 'border-red-500/50 bg-red-950/30 hover:border-red-400'
      : 'border-border bg-panel hover:border-slate-500';
  const directionColor = direction === 'LONG' ? 'text-green-400' : direction === 'SHORT' ? 'text-red-400' : 'text-slate-300';
  const hasScore = instrument.confidence != null && Number.isFinite(Number(instrument.confidence));

  return (
    <button
      type="button"
      data-instrument={instrument.symbol}
      aria-pressed={selected}
      className={`relative w-full min-h-[142px] p-4 text-left border rounded-xl transition-all hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500 ${colors} ${selected ? 'ring-2 ring-blue-400 shadow-lg shadow-blue-950/30' : ''}`}
      onClick={() => onSelect?.(instrument)}
    >
      <div className="font-black text-lg tracking-tight uppercase">{instrument.symbol}</div>
      <div className="text-xs text-muted mt-0.5 truncate">{instrument.name}</div>
      <div className={`mt-3 text-sm font-black ${directionColor}`}>
        {direction === 'LONG' ? '↑ LONG' : direction === 'SHORT' ? '↓ SHORT' : '— BRAK'}
      </div>
      <div className="mt-1 flex items-end justify-between gap-2">
        <span className={`text-3xl leading-none font-black ${directionColor}`}>
          {hasScore ? instrument.confidence : '—'}<span className="text-sm text-muted">/100</span>
        </span>
        {selected && <span className="text-[0.65rem] uppercase tracking-wider text-blue-300">Wybrany</span>}
      </div>
    </button>
  );
}
