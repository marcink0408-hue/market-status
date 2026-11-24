import { normalizeDecision, timeframeData } from '../../utils/market';

const RELATIONS = {
  main: 'Główny sygnał', confirms: 'Potwierdza', conflict: 'Konflikt',
  neutral: 'Neutralny / bez przewagi', missing: 'Brak danych',
};

function directionClass(direction) {
  if (direction === 'LONG') return 'text-green-400 border-green-500/30 bg-green-500/10';
  if (direction === 'SHORT') return 'text-red-400 border-red-500/30 bg-red-500/10';
  return 'text-slate-300 border-border bg-panel2';
}

const number = (value) => value == null || !Number.isFinite(Number(value))
  ? '—' : Number(value).toLocaleString('pl-PL', { maximumFractionDigits: 5 });

export default function TimeframeAlignment({ instrument }) {
  return (
    <section className="border border-border rounded-xl bg-panel/60 p-4">
      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <h3 className="font-bold">Zgodność interwałów</h3>
        <p className="text-xs text-muted">4H wyznacza kierunek · 1D kontekst · 1H moment wejścia</p>
      </div>
      <div className="grid md:grid-cols-3 gap-3">
        {['1D', '4H', '1H'].map((timeframe) => {
          const frame = timeframeData(instrument, timeframe);
          const alignment = instrument.timeframe_alignment?.[timeframe] || {};
          const direction = normalizeDecision(alignment.bias || frame.bias || frame.decision);
          const relation = alignment.status || (timeframe === '4H' ? 'main' : 'missing');
          const score = timeframe === '4H'
            ? instrument.confidence
            : alignment.confidence ?? frame.confidence;
          return (
            <article key={timeframe} className={`rounded-xl border p-4 ${directionClass(direction)}`} data-timeframe-card={timeframe}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-lg font-black">{timeframe}</span>
                <span className="text-lg font-black">{direction}</span>
              </div>
              <div className={`mt-2 text-sm font-semibold ${relation === 'conflict' ? 'text-red-400' : ''}`}>
                {RELATIONS[relation] || relation}
              </div>
              <div className="mt-1 text-xs text-muted">
                Ocena: {score == null ? 'brak danych' : `${score}/100`}
                {timeframe === '4H' && instrument.base_confidence != null ? ` · baza 4H ${instrument.base_confidence}/100` : ''}
              </div>
              {(frame.entry != null || frame.stop != null || frame.target != null) && (
                <div className="mt-3 pt-3 border-t border-border/60 grid grid-cols-3 gap-2 text-xs">
                  <span>Wejście ({timeframe})<b className="block text-text">{number(frame.entry)}</b></span>
                  <span>SL ({timeframe})<b className="block text-text">{number(frame.stop)}</b></span>
                  <span>TP ({timeframe})<b className="block text-text">{number(frame.target)}</b></span>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
