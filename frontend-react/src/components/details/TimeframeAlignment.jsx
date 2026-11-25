import { currentDecision, timeframeData } from '../../utils/market';

const RELATIONS = { main: 'GŁÓWNY KIERUNEK', confirms: 'ZGODNY', conflict: 'KONFLIKT', neutral: 'NEUTRALNY', missing: 'BRAK DANYCH' };

export default function TimeframeAlignment({ instrument }) {
  return (
    <section className="info-card h-fit">
      <h3>ZGODNOŚĆ INTERWAŁÓW</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {['1D', '4H', '1H'].map((timeframe) => {
          const frame = timeframeData(instrument, timeframe);
          const alignment = instrument.timeframe_alignment?.[timeframe] || {};
          const source = timeframe === '4H' ? instrument : frame;
          const direction = currentDecision({ ...source, decision: alignment.bias || source.bias || source.decision });
          const relation = alignment.status || (timeframe === '4H' ? 'main' : 'missing');
          const score = timeframe === '4H' ? instrument.confidence : alignment.confidence ?? frame.confidence;
          const directionClass = direction === 'LONG' ? 'direction-long' : direction === 'SHORT' ? 'direction-short' : 'direction-none';
          return (
            <article key={timeframe} className={`alignment-card ${relation === 'conflict' ? 'alignment-conflict' : ''}`} data-timeframe-card={timeframe}>
              <span className="text-xl font-black text-white">{timeframe}</span>
              <strong className={`mt-2 block text-2xl ${directionClass}`}>{direction}</strong>
              <span className="mt-2 block text-4xl font-black text-white">{score ?? '—'}<small>/100</small></span>
              <span className={`mt-2 block text-xs font-black ${relation === 'conflict' ? 'direction-short' : 'text-[var(--text-muted)]'}`}>{RELATIONS[relation] || relation}</span>
            </article>
          );
        })}
      </div>
      <p className="mt-4 text-center text-xs leading-relaxed text-[var(--text-muted)]">1D: kontekst · 4H: decyzja · 1H: precyzja wejścia</p>
    </section>
  );
}
