import TimeframeAlignment from './TimeframeAlignment';
import HarmonicPatterns from './HarmonicPatterns';
import ClassicPatterns from './ClassicPatterns';
import LatestCandles from './LatestCandles';
import SetupSummary from './SetupSummary';
import SignalJustification from './SignalJustification';

export default function InstrumentDetails({ instrument, data }) {
  if (!instrument) return null;
  return (
    <section className="grid gap-5 xl:grid-cols-2" aria-label="Formacje i zgodność interwałów">
      <SetupSummary instrument={instrument} />
      <TimeframeAlignment instrument={instrument} />
      <div className="space-y-5">
        <ClassicPatterns classicData={data?.classic} symbol={instrument.symbol} timeframe="4H" />
        <HarmonicPatterns instrument={instrument} />
        <LatestCandles instrument={instrument} />
        <SignalJustification instrument={instrument} />
      </div>
    </section>
  );
}
