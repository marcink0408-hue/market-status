import { timeframeData } from '../../utils/market';

export default function HarmonicPatterns({ instrument }) {
  const patterns = ['1D', '4H', '1H'].flatMap((timeframe) => (timeframeData(instrument, timeframe).harmonics || [])
    .filter((pattern) => ['forming', 'active'].includes(pattern.lifecycle || (pattern.active ? 'active' : 'historical')))
    .map((pattern) => ({ ...pattern, timeframe })));

  return (
    <section className="info-card">
      <h3>FORMACJE HARMONICZNE</h3>
      {!patterns.length ? <p className="empty-copy">Brak aktualnych formacji harmonicznych.</p> : (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {patterns.map((pattern, index) => {
            const bullish = pattern.direction === 'bullish';
            return (
              <article className="pattern-card" key={`${pattern.timeframe}-${pattern.name}-${pattern.time_D || pattern.time_C || index}`} data-pattern-timeframe={pattern.timeframe}>
                <span className="text-xs font-bold text-[var(--text-muted)]">{pattern.timeframe} · {pattern.lifecycle === 'forming' ? 'FORMUJE SIĘ · PRZ' : 'UKOŃCZONA · AKTUALNA'}</span>
                <strong className="mt-1 block text-xl text-white">{String(pattern.name).toUpperCase()}</strong>
                <span className={`mt-1 block text-2xl font-black ${bullish ? 'direction-long' : 'direction-short'}`}>{bullish ? 'WZROSTOWA' : 'SPADKOWA'}</span>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
