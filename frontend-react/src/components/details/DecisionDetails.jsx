const fmt = (v, digits = 2) => {
  if (v === null || v === undefined || v === '' || !Number.isFinite(Number(v))) return '—';
  return Number(v).toLocaleString('pl-PL', { minimumFractionDigits: digits, maximumFractionDigits: digits });
};

const numOrDash = (v) => (v == null || !Number.isFinite(Number(v)) ? '—' : fmt(v));

const decisionOf = (item) => {
  const d = String(item?.decision || '').toUpperCase();
  return ['LONG', 'SHORT'].includes(d) ? d : 'BRAK';
};

const directionLabel = (d) => (d === 'LONG' ? '↑ LONG' : d === 'SHORT' ? '↓ SHORT' : '— BRAK');

export default function DecisionDetails({ instrument }) {
  const d = decisionOf(instrument);
  const cls = d === 'LONG' ? 'text-green-400' : d === 'SHORT' ? 'text-red-400' : 'text-[#b2bfd1]';
  const rr = instrument.rr == null ? '—' : `1:${fmt(instrument.rr, 2)}`;

  return (
    <div className="bg-gradient-to-r from-[#17263a] to-[#111b2a] border border-border rounded-xl p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className={`text-xl font-black ${cls}`}>{directionLabel(d)}</div>
          <p className="text-xs text-muted mt-1">
            {d === 'BRAK'
              ? 'Brak potwierdzonego setupu.'
              : `Sygnał ${d === 'LONG' ? 'wzrostowy' : 'spadkowy'} · ocena punktowa ${instrument.confidence ?? 0}/100`}
          </p>
        </div>
        <div className="flex gap-2">
          <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">Renko —</span>
          <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">Harmoniczne —</span>
          <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">Świece —</span>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-4">
        <div className="border border-border rounded-lg bg-panel2 p-3">
          <div className="text-[0.72rem] text-muted">Wejście</div>
          <div className="font-black text-sm mt-1">{numOrDash(instrument.entry)}</div>
        </div>
        <div className="border border-border rounded-lg bg-panel2 p-3">
          <div className="text-[0.72rem] text-muted">Stop Loss</div>
          <div className="font-black text-sm mt-1 text-red-400">{numOrDash(instrument.stop)}</div>
        </div>
        <div className="border border-border rounded-lg bg-panel2 p-3">
          <div className="text-[0.72rem] text-muted">Zasięg / Take Profit</div>
          <div className="font-black text-sm mt-1 text-green-400">{numOrDash(instrument.target)}</div>
        </div>
        <div className="border border-border rounded-lg bg-panel2 p-3">
          <div className="text-[0.72rem] text-muted">Stosunek zysku do ryzyka</div>
          <div className="font-black text-sm mt-1">{rr}</div>
        </div>
        <div className="border border-border rounded-lg bg-panel2 p-3">
          <div className="text-[0.72rem] text-muted">Ocena sygnału</div>
          <div className="font-black text-sm mt-1">{instrument.confidence ?? 0}/100</div>
        </div>
      </div>
    </div>
  );
}