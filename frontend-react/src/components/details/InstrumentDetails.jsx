import DecisionDetails from './DecisionDetails';
import TimeframeAlignment from './TimeframeAlignment';

import SignalPillars from './SignalPillars';
import MarketContext from './MarketContext';
import HarmonicPatterns from './HarmonicPatterns';
import CandlePatterns from './CandlePatterns';
import ClassicPatterns from './ClassicPatterns';
import SignalJustification from './SignalJustification';

const findInstrumentBySymbol = (status, symbol) => {
  if (!status || !symbol) return null;
  const items = Array.isArray(status) ? status : (status.decisions || status.signals || status.results || []);
  const key = String(symbol).toLowerCase();
  return items.find((item) => String(item.symbol || '').toLowerCase() === key) || null;
};

export default function InstrumentDetails({ instrument, data }) {
  const fullInstrument = instrument ? findInstrumentBySymbol(data.status, instrument.symbol) : null;

  if (!instrument) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h2 className="text-sm font-semibold">Szczegóły instrumentu</h2>
          <p className="text-xs text-muted">Analiza 1D / 4H / 1H · wybierz instrument powyżej</p>
        </div>
        <div className="border border-dashed border-border rounded-xl bg-panel/50 p-6 text-center text-muted">
          Wybierz instrument z sekcji Instrumenty, aby zobaczyć szczegóły.
        </div>
      </section>
    );
  }

  const item = fullInstrument || instrument;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <h2 className="text-sm font-semibold">Szczegóły instrumentu</h2>
        <p className="text-xs text-muted">{item.name || instrument.symbol} · główny sygnał 4H · kontekst 1D i 1H</p>
      </div>

      <DecisionDetails instrument={item} />
      <TimeframeAlignment instrument={item} />
      <SignalPillars instrument={item} />
      <MarketContext instrument={item} />
      <HarmonicPatterns instrument={item} />
      <CandlePatterns instrument={item} />
      <ClassicPatterns classicData={data.classic} symbol={item.symbol} />
      <SignalJustification instrument={item} />
    </section>
  );
}