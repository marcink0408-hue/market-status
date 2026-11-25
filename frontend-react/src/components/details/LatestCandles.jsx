import { formatDate, formatPrice, timeframeData } from '../../utils/market';

export default function LatestCandles({ instrument }) {
  const patterns = ['1D', '4H', '1H'].flatMap((timeframe) => {
    const frame = timeframeData(instrument, timeframe);
    const candles = (frame.candles || []).filter((candle) => candle.direction !== 'neutral');
    if (!candles.length || !frame.last_time) return [];
    const latest = Math.max(...candles.map((candle) => Date.parse(candle.time) || 0));
    const lastBar = Date.parse(frame.last_time) || 0;
    if (latest !== lastBar) return [];
    return candles.filter((candle) => (Date.parse(candle.time) || 0) === latest)
      .map((candle) => ({ ...candle, timeframe, price: frame.last_close }));
  });

  return (
    <section className="info-card">
      <h3>FORMACJE ŚWIECOWE</h3>
      {!patterns.length ? <p className="empty-copy">Brak istotnej formacji na najnowszych świecach.</p> : (
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {patterns.map((pattern) => {
            const bullish = pattern.direction === 'bullish';
            return (
              <article className="candle-card" key={`${pattern.timeframe}-${pattern.name}-${pattern.time}`}>
                <strong>{String(pattern.name).toUpperCase()}</strong>
                <span className={`text-lg font-black ${bullish ? 'direction-long' : 'direction-short'}`}>{pattern.timeframe} · {bullish ? 'WZROSTOWA' : 'SPADKOWA'}</span>
                <span>DATA: {formatDate(pattern.time)}</span>
                <span>CENA: {formatPrice(pattern.price)}</span>
                <b>SYGNAŁ: {bullish ? 'MOŻLIWY WZROST' : 'MOŻLIWY SPADEK'}</b>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
