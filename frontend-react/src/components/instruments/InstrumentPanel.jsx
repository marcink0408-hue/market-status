import { useMarketData } from '../../hooks/useMarketData';
import InstrumentTile from './InstrumentTile';

function decisionOf(item) {
  const d = String(item?.decision || '').toUpperCase();
  return ['LONG', 'SHORT'].includes(d) ? d : 'BRAK';
}

export default function InstrumentPanel({ onSelect }) {
  const { data, overallStatus, error } = useMarketData();

  const raw = data.status || [];
  const items = Array.isArray(raw) ? raw : (raw.decisions || raw.signals || raw.results || []);

  const instruments = items.map((item) => ({
    ...item,
    symbol: item.symbol || item.instrument || '—',
    name: item.name || item.symbol || 'Instrument',
    decision: decisionOf(item),
    confidence: item.confidence ?? 0,
  }));

  const sorted = [...instruments].sort((a, b) => {
    const rank = (x) => (x.decision === 'BRAK' ? 1 : 0);
    return rank(a) - rank(b) || (Number(b.confidence) || 0) - (Number(a.confidence) || 0);
  });

  if (overallStatus === 'error') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h2 className="text-sm font-semibold">Instrumenty</h2>
          <p className="text-xs text-muted">Kliknij kafelek, aby zobaczyć wykres i szczegóły sygnału.</p>
        </div>
        <div className="border border-dashed border-border rounded-xl bg-panel/50 p-4 text-center text-red-400 text-sm">
          Błąd wczytywania danych: {error}
        </div>
      </section>
    );
  }

  if (overallStatus === 'loading' || !instruments.length) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h2 className="text-sm font-semibold">Instrumenty</h2>
          <p className="text-xs text-muted">Kliknij kafelek, aby zobaczyć wykres i szczegóły sygnału.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" id="instrument-tiles">
          <div className="flex flex-col h-full items-center justify-center p-4 border border-dashed border-border rounded-xl bg-panel/50 text-muted">
            Ładowanie danych instrumentów…
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <h2 className="text-sm font-semibold">Instrumenty</h2>
        <p className="text-xs text-muted">Kliknij kafelek, aby zobaczyć wykres i szczegóły sygnału.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" id="instrument-tiles">
        {sorted.map((instrument, idx) => (
          <InstrumentTile key={idx} instrument={instrument} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}