import { useMemo } from 'react';
import PriceChart from '../chart/PriceChart';
import InstrumentDetails from '../details/InstrumentDetails';
import DecisionDetails from '../details/DecisionDetails';
import { getChartPayload, statusItems, TIMEFRAMES } from '../../utils/market';

export default function MainWorkspace({ activeInstrument, data, timeframe, setTimeframe }) {
  const symbol = activeInstrument?.symbol;
  const instrument = useMemo(() => statusItems(data.status).find((item) => String(item.symbol).toLowerCase() === String(symbol).toLowerCase()) || activeInstrument, [data.status, activeInstrument, symbol]);
  const payload = useMemo(() => getChartPayload(data.ohlc, symbol, timeframe), [data.ohlc, symbol, timeframe]);

  return (
    <section className="space-y-7" aria-label="Panel decyzyjny">
      <DecisionDetails instrument={instrument} />
      <div className="chart-card">
        <div className="section-heading compact px-4 pt-5">
          <span className="heading-line" aria-hidden="true" />
          <h2>WYKRES I ANALIZA</h2>
          <span className="heading-line" aria-hidden="true" />
        </div>
        <div className="timeframe-tabs" role="group" aria-label="Interwał wykresu">
          {TIMEFRAMES.map((item) => (
            <button key={item} type="button" data-timeframe={item} aria-pressed={timeframe === item}
              onClick={() => setTimeframe(item)} className={timeframe === item ? 'timeframe-active' : ''}>{item}</button>
          ))}
        </div>
        <div className="h-[440px] w-full md:h-[560px]">
          {payload ? <PriceChart key={`${payload.symbol}:${payload.timeframe}`} payload={payload} /> : (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm text-[var(--text-muted)]">
              {activeInstrument ? `Brak danych ${timeframe} dla ${activeInstrument.symbol}.` : 'Wybierz instrument, aby wyświetlić wykres.'}
            </div>
          )}
        </div>
      </div>
      <InstrumentDetails instrument={instrument} data={data} />
    </section>
  );
}
