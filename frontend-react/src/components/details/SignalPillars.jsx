export default function SignalPillars({ instrument }) {
  const fil = instrument.filars || instrument.modules || {};

  return (
    <div className="flex gap-2">
      <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
        Renko {fil.renko ? '✓' : '—'}
      </span>
      <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
        Harmoniczne {fil.harmonic ? '✓' : '—'}
      </span>
      <span className="px-2 py-1 rounded border border-border bg-panel2 text-xs">
        Świece {fil.candle ? '✓' : '—'}
      </span>
    </div>
  );
}