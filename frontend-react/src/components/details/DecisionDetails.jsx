import { currentDecision, formatDate, formatPrice, normalizeDecision } from '../../utils/market';

const STATUS = {
  PENDING: 'OCZEKUJE NA WEJŚCIE', ACTIVE: 'AKTYWNY · PO WEJŚCIU',
  TAKE_PROFIT: 'TAKE PROFIT', STOP_LOSS: 'STOP LOSS', EXPIRED: 'WYGASŁY',
  INVALIDATED: 'ZANEGOWANY', NO_DATA: 'BRAK PEŁNYCH DANYCH', NONE: 'BRAK SETUPU',
};

function shortReasons(instrument, decision) {
  if (decision === 'BRAK') return [];
  const reasons = [];
  const harmonic = instrument.harmonic;
  if (harmonic && !['historical', 'invalidated', 'target_reached', 'expired'].includes(harmonic.lifecycle)) {
    reasons.push(`HARMONICZNA: ${harmonic.name} – ${harmonic.direction === 'bullish' ? 'WZROSTOWA' : 'SPADKOWA'}${harmonic.status === 'forming' ? ' · PRZ' : ''}`);
  }
  if (instrument.candle?.name) {
    reasons.push(`ŚWIECA: ${instrument.candle.name} – ${instrument.candle.direction === 'bullish' ? 'WZROSTOWA' : instrument.candle.direction === 'bearish' ? 'SPADKOWA' : 'NEUTRALNA'}`);
  }
  ['1H', '1D'].forEach((tf) => {
    if (instrument.timeframe_alignment?.[tf]?.status === 'conflict') reasons.push(`${tf}: KONFLIKT Z KIERUNKIEM 4H`);
  });
  return reasons.slice(0, 3);
}

export default function DecisionDetails({ instrument }) {
  if (!instrument) return null;
  const rawDecision = normalizeDecision(instrument.decision);
  const decision = currentDecision(instrument);
  const inferredStatus = decision === 'BRAK' && rawDecision !== 'BRAK' ? 'EXPIRED' : decision === 'BRAK' ? 'NONE' : 'ACTIVE';
  const status = instrument.signal_status || inferredStatus;
  const color = decision === 'LONG' ? 'direction-long' : decision === 'SHORT' ? 'direction-short' : 'direction-none';
  const canEnter = instrument.can_enter === true && status === 'PENDING' && decision !== 'BRAK';
  const showLevels = decision !== 'BRAK' && ['PENDING', 'ACTIVE'].includes(status);
  const reasons = shortReasons(instrument, decision);

  return (
    <section className={`main-signal signal-${decision.toLowerCase()}`} aria-labelledby="main-signal-heading" data-signal-status={status}>
      <div className="section-heading compact">
        <span className="heading-line" aria-hidden="true" />
        <h2 id="main-signal-heading">GŁÓWNY SYGNAŁ</h2>
        <span className="heading-line" aria-hidden="true" />
      </div>
      <div className="text-center">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-[var(--text-muted)]">{instrument.name || instrument.symbol} · decyzja 4H</p>
        <div className={`signal-direction ${color}`}>{decision === 'LONG' ? '↑ LONG' : decision === 'SHORT' ? '↓ SHORT' : '— BRAK'}</div>
        <div className="mt-2 text-3xl font-black text-white md:text-4xl">{instrument.confidence ?? '—'}<span className="text-lg text-[var(--text-muted)]">/100</span></div>
      </div>
      <div className={`signal-status ${canEnter ? 'signal-status-pending' : ''}`} role="status">
        <strong>{STATUS[status] || status}</strong>
        {canEnter && <span>Możliwe wejście do: {formatDate(instrument.signal_valid_until, true)}</span>}
        {status === 'ACTIVE' && <span>Entry zostało osiągnięte. Nie traktuj jako nowej okazji.</span>}
        {decision === 'BRAK' && rawDecision !== 'BRAK' && <span>Poprzedni kierunek {rawDecision} nie jest już aktywną okazją.</span>}
        {status === 'NONE' && <span>Brak potwierdzonej okazji do otwarcia pozycji.</span>}
      </div>
      {showLevels && (
        <div className="levels-grid">
          {[['WEJŚCIE', instrument.entry, 'level-entry'], ['STOP LOSS', instrument.stop, 'level-stop'], ['TAKE PROFIT', instrument.target, 'level-target']].map(([label, value, className]) => (
            <div className={`level-card ${className}`} key={label}><span>{label}</span><strong>{formatPrice(value, instrument.symbol)}</strong><small>{instrument.levels_timeframe || '4H'}</small></div>
          ))}
          <div className="level-card"><span>RELACJA ZYSK/RYZYKO</span><strong>{instrument.rr == null ? '—' : `1:${Number(instrument.rr).toLocaleString('pl-PL', { maximumFractionDigits: 2 })}`}</strong><small>R:R</small></div>
        </div>
      )}
      {!!reasons.length && <div className="signal-reasons">{reasons.map((reason) => <span key={reason}>{reason}</span>)}</div>}
    </section>
  );
}
