import { timeframeData } from '../../utils/market';

const number = (value) => value == null || !Number.isFinite(Number(value))
  ? 'Brak danych' : Number(value).toLocaleString('pl-PL', { maximumFractionDigits: 6 });

export default function MarketContext({ instrument }) {
  const daily = timeframeData(instrument, '1D');
  return (
    <section className="grid md:grid-cols-3 gap-3">
      {['1D', '4H', '1H'].map((timeframe) => {
        const frame = timeframeData(instrument, timeframe);
        return (
          <div key={timeframe} className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">ATR(14) · {timeframe}</div>
            <div className="font-bold mt-1">{number(frame.atr ?? (timeframe === '4H' ? instrument.atr : null))}</div>
          </div>
        );
      })}
      <div className="md:col-span-3 px-4 py-3 rounded-lg border border-border bg-panel2 text-sm">
        <span className="font-semibold">Kontekst D1: {instrument.daily_context || 'brak danych'}</span>
        <span className="text-muted ml-2">
          Renko: {daily.renko?.direction || 'brak'} · zakres 20 świec: {number(daily.market_levels?.recent_low)} – {number(daily.market_levels?.recent_high)}
        </span>
      </div>
    </section>
  );
}
