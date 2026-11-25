import InstrumentTile from './InstrumentTile';
import { currentDecision, statusItems } from '../../utils/market';

export default function InstrumentPanel({ data, overallStatus, error, activeSymbol, onSelect }) {
  const instruments = statusItems(data.status).map((item) => ({
    ...item,
    symbol: item.symbol || item.instrument || '—',
    name: item.name || item.symbol || 'Instrument',
    decision: currentDecision(item),
  }));
  const sorted = [...instruments].sort((a, b) => {
    const rank = (item) => (item.decision === 'BRAK' ? 1 : 0);
    return rank(a) - rank(b) || (Number(b.confidence) || 0) - (Number(a.confidence) || 0);
  });

  return (
    <section className="space-y-4" aria-labelledby="instruments-heading">
      <div className="section-heading">
        <span className="heading-line" aria-hidden="true" />
        <h2 id="instruments-heading">INSTRUMENTY</h2>
        <span className="heading-line" aria-hidden="true" />
      </div>
      {overallStatus === 'error' ? (
        <div className="border border-red-500/40 rounded-xl bg-red-500/10 p-4 text-red-300 text-sm">Błąd wczytywania danych: {error}</div>
      ) : overallStatus === 'loading' || !instruments.length ? (
        <div className="border border-dashed border-border rounded-xl bg-panel/50 p-6 text-center text-muted">Ładowanie danych instrumentów…</div>
      ) : (
        <div className="instrument-grid" id="instrument-tiles">
          {sorted.map((instrument) => (
            <InstrumentTile
              key={instrument.symbol}
              instrument={instrument}
              selected={String(activeSymbol).toLowerCase() === String(instrument.symbol).toLowerCase()}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </section>
  );
}
