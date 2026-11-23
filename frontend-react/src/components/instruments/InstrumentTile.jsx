export default function InstrumentTile({ instrument, onSelect }) {
  return (
    <button
      className="tile group relative w-full min-h-[148px] p-4 text-left border border-border rounded-xl bg-gradient-to-br from-[#162338] to-[#101723] text-text transition-all hover:-translate-y-1 hover:shadow-lg hover:border-blue-500/50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      onClick={() => onSelect?.(instrument)}
      role="tile"
      aria-label={`Szczegóły ${instrument.symbol || 'Instrument'}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-black text-lg tracking-tight">{instrument.symbol || '—'}</div>
          <div className="text-[0.77rem] text-muted mt-1">{instrument.name || instrument.symbol || 'Instrument'}</div>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[0.73rem] font-black uppercase tracking-wider whitespace-nowrap ${
          instrument.decision === 'LONG'
            ? 'bg-[#163f30] text-green-400'
            : instrument.decision === 'SHORT'
              ? 'bg-[#4b202a] text-red-400'
              : 'bg-[#29364a] text-[#b2bfd1]'
        }`}>
          {instrument.decision === 'LONG' ? '↑ LONG' : instrument.decision === 'SHORT' ? '↓ SHORT' : '— BRAK'}
        </span>
      </div>
      <div className="mt-5 flex items-end justify-between gap-3">
        <div>
          <div className="text-[0.74rem] text-muted">Ocena sygnału</div>
          <div className="font-black text-lg">
            {instrument.decision === 'BRAK' ? '—' : `${instrument.confidence ?? 0}/100`}
          </div>
        </div>
        <div className="text-[#9aaac0] text-xl">↗</div>
      </div>
    </button>
  );
}