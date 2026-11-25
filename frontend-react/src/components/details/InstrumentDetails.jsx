import TimeframeAlignment from './TimeframeAlignment';
import HarmonicPatterns from './HarmonicPatterns';
import LatestCandles from './LatestCandles';

export default function InstrumentDetails({ instrument }) {
  if (!instrument) return null;
  return (
    <section className="grid gap-5 xl:grid-cols-2" aria-label="Formacje i zgodność interwałów">
      <TimeframeAlignment instrument={instrument} />
      <div className="space-y-5">
        <HarmonicPatterns instrument={instrument} />
        <LatestCandles instrument={instrument} />
      </div>
    </section>
  );
}
