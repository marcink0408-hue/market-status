import { formatDate, formatPrice, timeframeData } from '../../utils/market';

const DEFAULT_LIMIT = 5;

export default function LatestCandles({ instrument, limit = DEFAULT_LIMIT }) {
  const allPatterns = ['1D', '4H', '1H'].flatMap((timeframe) => {
    const frame = timeframeData(instrument, timeframe);
    const candles = (frame.candles || []).filter((candle) => candle.direction !== 'neutral');
    return candles.map((candle) => ({ ...candle, timeframe, price: frame.last_close }));
  });

  if (!allPatterns.length) {
    return (
      <section className="info-card">
        <h3>FORMACJE ŚWIECOWE</h3>
        <p className="empty-copy">Brak istotnej formacji na najnowszych świecach.</p>
      </section>
    );
  }

  const sorted = allPatterns.sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
  const unique = [];
  const seen = new Set();
  for (const p of sorted) {
    const key = `${p.timeframe}|${p.time}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(p);
    if (unique.length >= limit) break;
  }

  const latestTime = Math.max(...allPatterns.map((p) => Date.parse(p.time) || 0));

  return (
    <section className="info-card">
      <h3>FORMACJE ŚWIECOWE</h3>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {unique.map((pattern) => {
          const bullish = pattern.direction === 'bullish';
          const isLatest = Date.parse(pattern.time) === latestTime;
          return (
            <article className="candle-card" key={`${pattern.timeframe}-${pattern.name}-${pattern.time}`}>
              <strong>{String(pattern.name).toUpperCase()}</strong>
              <span className={`text-lg font-black ${bullish ? 'direction-long' : 'direction-short'}`}>{pattern.timeframe} · {bullish ? 'WZROSTOWA' : 'SPADKOWA'}</span>
              <span>DATA: {formatDate(pattern.time)}</span>
              <span>CENA: {formatPrice(pattern.price)}</span>
              <b>SYGNAŁ: {bullish ? 'MOŻLIWY WZROST' : 'MOŻLIWY SPADEK'}</b>
              {isLatest && (
                <span className="text-xs text-[var(--text-muted)]">Ostatnia świeca – weryfikuj zamknięcie</span>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
