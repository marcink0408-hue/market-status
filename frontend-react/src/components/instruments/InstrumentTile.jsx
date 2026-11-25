export default function InstrumentTile({ instrument, selected, onSelect }) {
  const direction = instrument.decision;
  const directionClass = direction === 'LONG' ? 'direction-long' : direction === 'SHORT' ? 'direction-short' : 'direction-none';
  const icons = { gold: 'AU', silver: 'AG', copper: 'CU', eurusd: '€', eurpln: '€', usdpln: '$', usdjpy: '¥', us500: 'S&P', w20: 'W20', eu50: 'E50', uk100: 'UK', bitcoin: '₿', btc: '₿' };
  const hasScore = instrument.confidence != null && Number.isFinite(Number(instrument.confidence));

  return (
    <button type="button" data-instrument={instrument.symbol} aria-pressed={selected}
      className={`instrument-tile ${selected ? 'instrument-selected' : ''}`} onClick={() => onSelect?.(instrument)}>
      <span className="text-lg font-black uppercase tracking-wide text-white md:text-xl">{instrument.name || instrument.symbol}</span>
      <span className="instrument-icon" aria-hidden="true">{icons[String(instrument.symbol).toLowerCase()] || String(instrument.symbol).slice(0, 3).toUpperCase()}</span>
      <span className={`text-xl font-black ${directionClass}`}>{direction === 'LONG' ? '↑ LONG' : direction === 'SHORT' ? '↓ SHORT' : '— BRAK'}</span>
      <span className="text-sm font-bold text-[var(--text-muted)]">{hasScore ? instrument.confidence : '—'}<span className="text-xs">/100</span></span>
      {selected && <span className="selected-label">WYBRANY</span>}
    </button>
  );
}
