import { useEffect, useMemo, useState } from 'react';
import PriceChart from '../chart/PriceChart';
import InstrumentDetails from '../details/InstrumentDetails';
import { getChartPayload, TIMEFRAMES } from '../../utils/market';

export default function MainWorkspace({ activeInstrument, data }) {
  const [timeframe, setTimeframe] = useState('4H');
  const symbol = activeInstrument?.symbol;

  useEffect(() => setTimeframe('4H'), [symbol]);
  const payload = useMemo(
    () => getChartPayload(data.ohlc, symbol, timeframe),
    [data.ohlc, symbol, timeframe],
  );

  return (
    <section className="space-y-6" aria-label="Obszar roboczy">
      <div className="border border-border rounded-xl bg-[#080e17] overflow-hidden">
        <div className="flex items-center justify-between gap-3 p-3 md:p-4 border-b border-border flex-wrap">
          <div>
            <h2 className="font-bold">Obszar roboczy A</h2>
            <p className="text-xs text-muted mt-1">{activeInstrument ? `${activeInstrument.name} · ${timeframe}` : 'Wybierz instrument'}</p>
          </div>
          <div className="flex rounded-lg border border-border overflow-hidden" aria-label="Interwał wykresu">
            {TIMEFRAMES.map((item) => (
              <button
                key={item}
                type="button"
                data-timeframe={item}
                aria-pressed={timeframe === item}
                onClick={() => setTimeframe(item)}
                className={`px-4 py-2 text-sm font-bold transition-colors ${timeframe === item ? 'bg-blue-500 text-slate-950' : 'bg-panel text-muted hover:text-text'}`}
              >{item}</button>
            ))}
          </div>
        </div>
        <div className="h-[480px] md:h-[560px] w-full">
          {payload ? (
            <PriceChart key={`${payload.symbol}:${payload.timeframe}`} payload={payload} />
          ) : (
            <div className="h-full flex items-center justify-center text-muted text-sm p-6 text-center">
              {activeInstrument ? `Brak danych ${timeframe} dla ${activeInstrument.symbol}.` : 'Wybierz instrument, aby wyświetlić wykres.'}
            </div>
          )}
        </div>
      </div>
      <InstrumentDetails instrument={activeInstrument} data={data} />
    </section>
  );
}
