import { formatDate, formatPrice } from '../../utils/market';

export default function SetupSummary({ instrument }) {
  const er = instrument?.entry_readiness;
  const hasReadiness = !!er;

  if (!instrument) return null;

  const directionLabel = hasReadiness && er.direction === 'LONG'
    ? '↑ LONG'
    : hasReadiness && er.direction === 'SHORT'
      ? '↓ SHORT'
      : '— BRAK KIERUNKU';
  const directionClass = hasReadiness && er.direction === 'LONG'
    ? 'direction-long'
    : hasReadiness && er.direction === 'SHORT'
      ? 'direction-short'
      : 'direction-none';

  const readiness = hasReadiness ? er.readiness_pct : null;
  const stage = hasReadiness ? er.stage : 'BRAK DANYCH';
  const setupStatus = hasReadiness ? er.setup_status : 'BRAK DANYCH';
  const entryAllowed = hasReadiness ? er.entry_allowed : false;
  const blockers = hasReadiness ? (er.blockers || []) : [];
  const missing = hasReadiness ? (er.missing || []) : [];
  const invalidationLevel = hasReadiness ? er.invalidation_level : null;
  const nextCheckTime = hasReadiness ? er.next_check_time : null;
  const dataAsOf = hasReadiness ? er.data_as_of : null;
  const entry = hasReadiness ? er.entry : null;
  const stop = hasReadiness ? er.stop : null;
  const target = hasReadiness ? er.target : null;
  const rr = hasReadiness ? er.rr : null;

  const scores = hasReadiness ? er.scores : {};
  const longScore = scores.LONG ? scores.LONG.readiness_pct : null;
  const shortScore = scores.SHORT ? scores.SHORT.readiness_pct : null;

  return (
    <section className="space-y-5" aria-label="Podsumowanie setupu">
      <div className="section-heading compact">
        <span className="heading-line" aria-hidden="true" />
        <h2>PODSUMOWANIE SETUPU</h2>
        <span className="heading-line" aria-hidden="true" />
      </div>

      {hasReadiness ? (
        <>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
              <div className="text-xs text-muted">INSTRUMENT</div>
              <div className="font-bold mt-1">{instrument.name || instrument.symbol}</div>
            </div>
            <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
              <div className="text-xs text-muted">GŁÓWNY INTERWAŁ</div>
              <div className="font-bold mt-1">{er.main_timeframe || '4H'}</div>
            </div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-muted">KIERUNEK</div>
              <span className={`text-lg font-black ${directionClass}`}>{directionLabel}</span>
            </div>
            <div className="mt-2">
              <div className="text-xs text-muted">ETAP SETUPU</div>
              <div className="font-bold mt-1">{stage}</div>
            </div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">GOTOWOŚĆ SETUPU</div>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-3xl font-black">{readiness}%</span>
              <span className="text-sm text-muted">/100</span>
            </div>
            <p className="mt-1 text-[0.65rem] text-[var(--text-muted)] leading-relaxed">
              Gotowość oznacza stopień spełnienia warunków setupu, nie szansę na zysk ani prawdopodobieństwo sukcesu.
            </p>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">NAJWAŻNIEJSZY BRAKUJĄCY WARUNEK</div>
            <div className="mt-1 text-sm">
              {blockers.length > 0 ? (
                <span>{blockers[0]}</span>
              ) : missing.length > 0 ? (
                <span>{missing[0]}</span>
              ) : (
                <span className="text-[var(--text-muted)]">Brak brakujących warunków</span>
              )}
            </div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">POZIOM UNIĄCZNIENIA</div>
            <div className="mt-1">
              {invalidationLevel != null ? formatPrice(invalidationLevel, instrument.symbol) : '—'}
            </div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">STATUS SETUPU</div>
            <div className="mt-1 font-bold">{setupStatus}</div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">NAJBLIŻSZA OCENA WARUNKÓW</div>
            <div className="mt-1 text-sm">
              {nextCheckTime ? formatDate(nextCheckTime, true) : '—'}
            </div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">DANE Z:</div>
            <div className="mt-1 text-sm">
              {dataAsOf ? formatDate(dataAsOf, true) : '—'}
            </div>
          </div>

          <div className="px-4 py-3 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">ZGODNOŚĆ INTERWAŁÓW</div>
            <div className="mt-1 space-y-1 text-sm">
              <div>1D — kierunek: {longScore != null ? longScore + '%' : '—'} / {shortScore != null ? shortScore + '%' : '—'}</div>
              <div>4H — setup: {readiness}%</div>
              <div>1H — wyzwalacz: {er.trigger_level != null ? 'potwierdzony' : 'brak potwierdzenia'}</div>
            </div>
          </div>
        </>
      ) : (
        <div className="border border-dashed border-border rounded-lg bg-panel/50 p-6 text-center text-muted">
          Brak danych nowego modelu gotowości (entry_readiness).
        </div>
      )}

      {hasReadiness && setupStatus === 'POTWIERDZONY' && (
        <div className="border border-amber-500/40 rounded-lg bg-amber-500/10 p-3 text-amber-200 text-sm">
          Warunki setupu spełnione. To nie jest rekomendacja inwestycyjna.
        </div>
      )}

      {hasReadiness && entryAllowed && entry != null && stop != null && target != null && rr != null && (
        <div className="grid gap-2 md:grid-cols-4">
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">ENTRY</div>
            <div className="font-bold">{formatPrice(entry, instrument.symbol)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">STOP LOSS</div>
            <div className="font-bold">{formatPrice(stop, instrument.symbol)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">TAKE PROFIT</div>
            <div className="font-bold">{formatPrice(target, instrument.symbol)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">R:R</div>
            <div className="font-bold">1:{rr.toFixed(2)}</div>
          </div>
        </div>
      )}

      <div className="border border-border rounded-lg bg-panel2 p-3">
        <p className="text-[0.65rem] text-[var(--text-muted)] leading-relaxed">
          {blockers.length > 0 ? 'Blokady wejścia: ' + [...new Set(blockers)].join(', ') + '.' : ''}
        </p>
      </div>
    </section>
  );
}