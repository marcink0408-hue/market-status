import { timeframeData } from '../../utils/market';

const DESCRIPTIONS = {
  gartley: 'Klasyczna formacja harmoniczna XABCD.',
  bat: 'Formacja oparta na proporcjach Fibonacciego.',
  butterfly: 'Formacja z punktem D poza punktem X.',
  crab: 'Formacja z wydłużonym ruchem.',
  'deep crab': 'Odmiana formacji Crab.',
};
const LIFECYCLE = { active: 'Aktywna', historical: 'Historyczna', forming: 'Kształtująca się' };
const number = (value) => value == null || !Number.isFinite(Number(value))
  ? '—' : Number(value).toLocaleString('pl-PL', { maximumFractionDigits: 5 });

function HarmonicSvg() {
  return (
    <svg viewBox="0 0 80 65" aria-hidden="true" className="w-16 h-16 shrink-0">
      <polyline points="5,13 23,50 39,27 55,43 73,12" fill="none" stroke="#70b7ff" strokeWidth="2.5" />
      {[['5','13'],['23','50'],['39','27'],['55','43'],['73','12']].map(([cx, cy]) => <circle key={cx} cx={cx} cy={cy} r="4" fill="#f7c66b" />)}
    </svg>
  );
}

export default function HarmonicPatterns({ instrument }) {
  const groups = ['1D', '4H', '1H'].map((timeframe) => ({
    timeframe,
    patterns: timeframeData(instrument, timeframe).harmonics || [],
  }));
  const total = groups.reduce((sum, group) => sum + group.patterns.length, 0);

  return (
    <section className="border border-border rounded-xl bg-panel/60 p-4 space-y-4">
      <h3 className="font-bold">Formacje harmoniczne · podział na interwały</h3>
      {!total && <p className="text-muted text-sm">Brak wykrytych formacji harmonicznych na 1D, 4H i 1H.</p>}
      {groups.map(({ timeframe, patterns }) => (
        <div key={timeframe} className="space-y-3" data-harmonic-timeframe={timeframe}>
          <h4 className="text-sm font-bold text-blue-300 border-b border-border pb-2">{timeframe} · {patterns.length}</h4>
          {patterns.map((pattern, index) => {
            const bullish = pattern.direction === 'bullish';
            const lifecycle = pattern.lifecycle || (pattern.status === 'forming' ? 'forming' : 'active');
            const key = `${timeframe}-${pattern.name}-${pattern.created_at || pattern.time_D || pattern.time_C}-${index}`;
            return (
              <article key={key} className="border border-border rounded-lg bg-panel2 p-4" data-pattern-symbol={pattern.symbol || instrument.symbol} data-pattern-timeframe={timeframe}>
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold">{pattern.name}</span>
                      <span className="text-xs px-2 py-0.5 rounded border border-blue-500/30 text-blue-300">{timeframe}</span>
                      <span className={`text-xs font-bold ${bullish ? 'text-green-400' : 'text-red-400'}`}>{bullish ? 'Wzrostowa' : 'Spadkowa'}</span>
                      <span className={`text-xs ${lifecycle === 'historical' ? 'text-muted' : 'text-amber-400'}`}>{LIFECYCLE[lifecycle]}</span>
                    </div>
                    <p className="text-xs text-muted mt-1">{DESCRIPTIONS[String(pattern.name).toLowerCase()] || 'Formacja harmoniczna XABCD.'}</p>
                    <p className="text-[0.7rem] text-muted mt-1">Utworzenie: {pattern.created_at || pattern.time_D || pattern.time_C || '—'}</p>
                  </div>
                  {pattern.error != null && <span className="text-xs text-muted">Błąd proporcji: {Number(pattern.error).toFixed(3)}</span>}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3">
                  {['X', 'A', 'B', 'C', 'D'].map((point) => {
                    const value = point === 'D' && pattern.D == null ? pattern.D_projected : pattern[point];
                    return (
                      <div key={point} className="rounded bg-bg/50 p-2 text-center">
                        <div className="text-[0.65rem] text-muted">{point}{point === 'D' && pattern.D == null ? ' (proj.)' : ''}</div>
                        <div className="text-xs font-mono mt-1">{number(value)}</div>
                        <div className="text-[0.6rem] text-muted mt-1">{pattern[`time_${point}`]?.slice(0, 10) || '—'}</div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-3 mt-2"><HarmonicSvg /><span className="text-xs text-muted">Rzeczywiste poziomy XABCD · {instrument.symbol} · {timeframe}</span></div>
              </article>
            );
          })}
        </div>
      ))}
    </section>
  );
}
