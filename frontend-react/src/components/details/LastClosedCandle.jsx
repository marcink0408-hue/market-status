import { formatPrice, formatDate } from '../../utils/market';

const DIRECTION_LABEL = { bullish: 'WZROSTOWA', bearish: 'SPADKOWA', neutral: 'NEUTRALNA' };
const DIRECTION_CLASS = { bullish: 'direction-long', bearish: 'direction-short', neutral: 'direction-none' };
const BODY_CLASS_LABEL = { very_small: 'bardzo mały', small: 'mały', medium: 'średni', large: 'duży' };
const WICK_CLASS_LABEL = { short: 'krótki', medium: 'średni', long: 'długi' };
const CLOSE_LOCATION_LABEL = { upper: 'górnej', middle: 'środkowej', lower: 'dolnej' };

export default function LastClosedCandle({ instrument, timeframe = '4H' }) {
  if (!instrument) return null;
  const tfKey = timeframe === '1D' ? '1D' : timeframe;
  const tfData = instrument?.timeframes?.[tfKey] || (timeframe === '1D' ? instrument?.timeframes?.Daily : null) || {};
  const candle = tfData.last_closed_candle;
  if (!candle) {
    return (
      <section className="info-card h-fit"><h3>OSTATNIA ZAMKNIĘTA ŚWIECA</h3>
        <div className="border border-dashed border-border rounded-lg bg-panel/50 p-6 text-center text-muted">
          Brak danych o ostatniej zamkniętej świece ({tfKey}).
        </div></section>
    );
  }
  const direction = String(candle.body_direction || '').toLowerCase();
  const directionLabel = DIRECTION_LABEL[direction] || 'NIEZNANA';
  const directionClass = DIRECTION_CLASS[direction] || 'direction-none';
  const bodyClass = candle.body_class ? BODY_CLASS_LABEL[candle.body_class] : '—';
  const upperWickClass = candle.upper_wick_class ? WICK_CLASS_LABEL[candle.upper_wick_class] : '—';
  const lowerWickClass = candle.lower_wick_class ? WICK_CLASS_LABEL[candle.lower_wick_class] : '—';
  const closeLoc = CLOSE_LOCATION_LABEL[candle.close_location] || '—';
  const closedAt = candle.closed_at ? formatDate(candle.closed_at, true) : '—';
  const p = (v) => formatPrice(v, instrument.symbol);
  return (
    <section className="info-card h-fit">
      <h3>OSTATNIA ZAMKNIĘTA ŚWIECA</h3>
      <div className="mt-4 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-xs font-bold ${directionClass}`}>{directionLabel}</span>
          {candle.description ? (
            <span className="ml-auto text-[0.7rem] text-[var(--text-muted)] italic">{candle.description}</span>
          ) : null}
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">INTERWAŁ</div><div className="font-bold mt-1">{tfKey}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">STATUS</div>
            <div className={`font-bold mt-1 ${candle.is_closed === true ? 'text-green-400' : 'text-[var(--text-muted)]'}`}>
              {candle.is_closed === true ? 'ZAMKNIĘTA' : 'OTWARTA'}
            </div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">OPEN</div><div className="font-bold mt-1">{p(candle.open)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">HIGH</div><div className="font-bold mt-1">{p(candle.high)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">LOW</div><div className="font-bold mt-1">{p(candle.low)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">CLOSE</div><div className="font-bold mt-1">{p(candle.close)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">KORPUS</div><div className="font-bold mt-1">{p(candle.body)}</div>
            <div className="text-[0.65rem] mt-0.5 text-[var(--text-muted)]">{bodyClass}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">GÓRNY KNOT</div><div className="font-bold mt-1">{p(candle.upper_wick)}</div>
            <div className="text-[0.65rem] mt-0.5 text-[var(--text-muted)]">{upperWickClass}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">DOLNY KNOT</div><div className="font-bold mt-1">{p(candle.lower_wick)}</div>
            <div className="text-[0.65rem] mt-0.5 text-[var(--text-muted)]">{lowerWickClass}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">ZAKRES (H−L)</div><div className="font-bold mt-1">{p(candle.range)}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">UDZIAŁ KORPUSU</div>
            <div className="font-bold mt-1">{candle.body_pct != null ? `${(candle.body_pct * 100).toFixed(0)}%` : '—'}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">POŁOŻENIE ZAMKNIĘCIA</div><div className="font-bold mt-1">{closeLoc}</div>
          </div>
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-xs text-muted">CZAS ZAMKNIĘCIA (UTC)</div><div className="font-bold mt-1">{closedAt}</div>
          </div>
        </div>
        {candle.description && (
          <div className="px-3 py-2 rounded-lg border border-border bg-panel2">
            <div className="text-[0.65rem] text-[var(--text-muted)] leading-relaxed">{candle.description}</div>
          </div>
        )}
      </div>
    </section>
  );
}