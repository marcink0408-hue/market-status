import PriceChart from '../chart/PriceChart';
import InstrumentDetails from '../details/InstrumentDetails';

const findChartPayload = (ohlc, symbol) => {
  if (!ohlc || !ohlc.symbols || !symbol) return null;
  const sym = String(symbol).toLowerCase();
  return ohlc.symbols[sym] || ohlc.symbols[symbol] || null;
};

export default function MainWorkspace({ activeInstrument, data }) {
  const chartPayload = activeInstrument ? findChartPayload(data.ohlc, activeInstrument.symbol) : null;
  const candles = chartPayload?.candles || [];
  const levels = chartPayload?.levels || {};
  const harmonics = chartPayload?.harmonics || [];

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <h2 className="text-sm font-semibold">Obszar roboczy</h2>
        <p className="text-xs text-muted">
          {activeInstrument ? `Wybrany instrument: ${activeInstrument.symbol}` : 'Wybierz instrument z panelu po lewej'}
        </p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="border border-border rounded-xl bg-[#080e17] p-1 flex flex-col h-[420px] min-h-[300px]">
          <div className="flex-1 flex items-center justify-center border-b border-border text-muted text-sm">
            {activeInstrument ? `Wykres 4H · ${activeInstrument.symbol}` : 'Wybierz instrument z panelu po lewej'}
          </div>
          {candles.length > 0 ? (
            <div className="flex-1">
              <PriceChart candles={candles} levels={levels} harmonics={harmonics} />
            </div>
          ) : null}
        </div>
        <InstrumentDetails instrument={activeInstrument} data={data} />
      </div>
    </section>
  );
}