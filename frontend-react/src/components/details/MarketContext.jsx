const numOrDash = (v) => (v == null || !Number.isFinite(Number(v)) ? '—' : Number(v).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));

export default function MarketContext({ instrument }) {
  const atr = instrument.atr_4h ?? instrument.atr;

  return (
    <div className="flex gap-2 flex-wrap">
      <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
        Kontekst D1: {instrument.daily_context || 'brak'}
      </span>
      <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
        ATR(14): {numOrDash(atr)}
      </span>
    </div>
  );
}