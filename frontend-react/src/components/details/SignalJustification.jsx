import { formatDate, formatPrice } from '../../utils/market';

const numOrDash = (v) => (v == null || !Number.isFinite(Number(v)) ? 'Brak danych' : Number(v).toLocaleString('pl-PL', { maximumFractionDigits: 6 }));

const statusTag = (kind) => {
  switch (kind) {
    case 'confirmed': return <span className="text-xs font-bold text-green-400">Fakt potwierdzony</span>;
    case 'failed': return <span className="text-xs font-bold text-red-400">Warunek niespełniony</span>;
    default: return <span className="text-xs font-bold text-[var(--text-muted)]">Brak danych</span>;
  }
};

export default function SignalJustification({ instrument, symbol }) {
  const sym = symbol || instrument?.symbol;
  const er = instrument?.entry_readiness || {};
  const tfAlignment = instrument?.timeframe_alignment || {};
  const timeframes = instrument?.timeframes || {};
  const tf4h = timeframes['4H'] || {};
  const tf1h = timeframes['1H'] || {};
  const tf1d = timeframes['1D'] || timeframes['Daily'] || {};
  const criteria = Array.isArray(er.criteria) ? er.criteria : [];
  const blockers = Array.isArray(er.blockers) ? er.blockers : [];
  const missing = Array.isArray(er.missing) ? er.missing : [];
  const direction = er.direction || 'NONE';
  const entry = er.entry ?? instrument?.entry;
  const stop = er.stop ?? instrument?.stop;
  const target = er.target ?? instrument?.target;
  const rr = er.rr ?? instrument?.rr;

  return (
    <div className="border border-border rounded-lg bg-panel2 p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-semibold">🧭 Uzasadnienie sygnału</span>
        <span className={`ml-auto text-xs ${direction === 'LONG' ? 'text-green-400' : direction === 'SHORT' ? 'text-red-400' : 'text-[var(--text-muted)]'}`}>
          Kierunek: {direction}
        </span>
      </div>
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-blue-400">1. Kontekst 1D</span>
          {statusTag('data')}
        </div>
        <p className="text-sm text-muted">{instrument?.timeframe_alignment?.['1D'] ? `${instrument.timeframe_alignment['1D'].bias || 'BRAK'} (${instrument.timeframe_alignment['1D'].status || '—'})` : 'Brak danych'}</p>
      </div>
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-blue-400">2. Struktura 4H</span>
          {statusTag('data')}
        </div>
        <p className="text-sm text-muted">{criteria.find((c) => c.id === 'structure_4h') ? `${criteria.find((c) => c.id === 'structure_4h').points}/${criteria.find((c) => c.id === 'structure_4h').max} pkt` : 'Brak danych'}</p>
      </div>
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-blue-400">3. Potwierdzenie 1H (wyzwalacz)</span>
          {statusTag('data')}
        </div>
        <p className="text-sm text-muted">{criteria.find((c) => c.id === 'trigger') ? `${criteria.find((c) => c.id === 'trigger').points}/${criteria.find((c) => c.id === 'trigger').max} pkt` : 'Brak danych'}</p>
        {er.trigger_level != null && <p className="text-[0.65rem] text-[var(--text-muted)] mt-1">Poziom wyzwalacza 1H: {formatPrice(er.trigger_level, sym)}</p>}
      </div>

      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-blue-400">4. Formacje świecowe (1H · 4H · 1D)</span>
        </div>
        <p className="text-sm text-muted">1H: {tf1h.candles && tf1h.candles.length ? `O ${numOrDash(tf1h.candles[tf1h.candles.length-1].open)} C ${numOrDash(tf1h.candles[tf1h.candles.length-1].close)}` : 'Brak danych'}</p>
        <p className="text-sm text-muted">4H: {tf4h.candles && tf4h.candles.length ? `O ${numOrDash(tf4h.candles[tf4h.candles.length-1].open)} C ${numOrDash(tf4h.candles[tf4h.candles.length-1].close)}` : 'Brak danych'}</p>
        <p className="text-sm text-muted">1D: {tf1d.candles && tf1d.candles.length ? `O ${numOrDash(tf1d.candles[tf1d.candles.length-1].open)} C ${numOrDash(tf1d.candles[tf1d.candles.length-1].close)}` : 'Brak danych'}</p>
      </div>
      <div className="mb-3">
        <div className="text-xs font-bold text-blue-400 mb-1">5. Strefy S/R (4H)</div>
        <p className="text-sm text-muted">{Array.isArray(tf4h.sr_zones) && tf4h.sr_zones.length ? tf4h.sr_zones.slice(0, 6).map((z) => `${z.type === 'SUPPORT' ? 'Wsparcie' : 'Opor'} ${numOrDash(z.center)}`).join(' · ') : 'Brak danych'}</p>
      </div>
      <div className="mb-3">
        <div className="text-xs font-bold text-blue-400 mb-1">6. Entry / SL / TP / RR (źródło: setup 4H)</div>
        <div className="grid gap-1 md:grid-cols-4 text-sm">
          <div className="px-2 py-1 rounded border border-border bg-panel2"><div className="text-[0.65rem] text-[var(--text-muted)]">ENTRY</div><div className="font-bold">{entry != null ? formatPrice(entry, sym) : 'Brak danych'}</div></div>
          <div className="px-2 py-1 rounded border border-border bg-panel2"><div className="text-[0.65rem] text-[var(--text-muted)]">STOP LOSS</div><div className="font-bold">{stop != null ? formatPrice(stop, sym) : 'Brak danych'}</div></div>
          <div className="px-2 py-1 rounded border border-border bg-panel2"><div className="text-[0.65rem] text-[var(--text-muted)]">TAKE PROFIT</div><div className="font-bold">{target != null ? formatPrice(target, sym) : 'Brak danych'}</div></div>
          <div className="px-2 py-1 rounded border border-border bg-panel2"><div className="text-[0.65rem] text-[var(--text-muted)]">R:R</div><div className="font-bold">{rr != null ? `1:${Number(rr).toFixed(2)}` : 'Brak danych'}</div></div>
        </div>
      </div>
      <div className="mb-3">
        <div className="text-xs font-bold text-blue-400 mb-1">7. Blokady i brakujące warunki</div>
        <div className="space-y-1 text-sm">
          {blockers.length ? (<><p className="text-red-400">Blokady:</p><ul className="list-disc list-inside space-y-1 text-sm text-red-300/80">{[...new Set(blockers)].map((b, i) => <li key={i}>{b}</li>)}</ul></>) : (<p className="text-[var(--text-muted)]">Brak blokad wejścia.</p>)}
          {missing.length ? (<><p className="text-amber-400 mt-2">Brakujące warunki:</p><ul className="list-disc list-inside space-y-1 text-sm text-amber-300/80">{[...new Set(missing)].map((m, i) => <li key={i}>{m}</li>)}</ul></>) : (<p className="text-[var(--text-muted)] mt-2">Brak brakujących warunków.</p>)}
        </div>
      </div>
      <p className="mt-3 text-[0.65rem] text-[var(--text-muted)] leading-relaxed">
        Gotowość setupu to stopień spełnienia warunków, nie szansa na zysk. Brak harmonicznej ani formacji świecowej nie jest traktowane automatycznie jako blokada.
      </p>
    </div>
  );
}
