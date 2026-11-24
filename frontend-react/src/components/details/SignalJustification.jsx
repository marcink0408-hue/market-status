const numOrDash = (v) => (v == null || !Number.isFinite(Number(v)) ? 'Brak danych' : Number(v).toLocaleString('pl-PL', { maximumFractionDigits: 6 }));

export default function SignalJustification({ instrument }) {
  const reasons = instrument?.reasons || [];
  const atr = instrument.atr_4h ?? instrument.atr;

  return (
    <div className="border border-border rounded-lg bg-panel2 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold">🧭 Uzasadnienie sygnału</span>
      </div>
      {reasons.length ? (
        <ul className="space-y-2 text-sm text-muted">
          {reasons.map((r, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-amber-400">▸</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted text-sm">Brak opisu uzasadnienia.</p>
      )}
      <div className="mt-4 pt-4 border-t border-border flex gap-2 flex-wrap">
        <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
          Kontekst D1: {instrument?.daily_align === 1 ? 'zgodny' : instrument?.daily_align === -1 ? 'przeciwny' : 'neutralny'}
        </span>
        <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
          ATR(14) · 4H: {numOrDash(atr)}
        </span>
      </div>
    </div>
  );
}