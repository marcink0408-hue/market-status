import { currentDecision, timeframeData } from '../../utils/market';

const RELATIONS = { main: 'GŁÓWNY', confirms: 'ZGODNY', conflict: 'KONFLIKT', neutral: 'NEUTRALNY', missing: 'BRAK DANYCH' };

export default function TimeframeAlignment({ instrument }) {
  const alignment = instrument?.timeframe_alignment || {};

  return (
    <section className="info-card h-fit">
      <h3>ZGODNOŚĆ INTERWAŁÓW</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {['1D', '4H', '1H'].map((timeframe) => {
          const tfAlign = alignment[timeframe] || {};
          const available = tfAlign.available !== false;
          const bias = tfAlign.bias || 'BRAK';
          const direction = currentDecision({ decision: bias });
          const score = tfAlign.confidence != null ? tfAlign.confidence : tfAlign.score;
          const relation = tfAlign.status || (timeframe === '4H' ? 'main' : available ? 'neutral' : 'missing');
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
