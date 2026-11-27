const NAMES = {
  double_top: 'Podwójny szczyt', double_bottom: 'Podwójne dno',
  head_and_shoulders: 'Głowa z ramionami', inverse_head_and_shoulders: 'Odwrócona głowa z ramionami',
  triangle: 'Trójkąt', wedge: 'Klin', flag: 'Flaga / Chorągiewka', channel: 'Kanał',
};

const SUBTYPE_LABELS = {
  symmetrical: 'symetryczny', ascending: 'wzrostowy', descending: 'spadkowy',
  rising: 'wzrostowy', falling: 'spadkowy', flat: 'boczny',
  reversal: 'odwrócenie',
};

const STATUS_LABELS = {
  'FORMUJĄCA SIĘ': 'Formuje się',
  'POTWIERDZONA': 'Potwierdzona',
  'WYBITA': 'Wybita',
  'RETEST': 'Retest',
  'UNIEWAŻNIONA': 'Unieważniona',
  'WYGASŁA': 'Wygasła',
};

const STATUS_COLORS = {
  'FORMUJĄCA SIĘ': 'text-yellow-400',
  'POTWIERDZONA': 'text-blue-400',
  'WYBITA': 'text-red-400',
  'RETEST': 'text-purple-400',
  'UNIEWAŻNIONA': 'text-gray-400',
  'WYGASŁA': 'text-gray-500',
};

export default function ClassicPatterns({ classicData, symbol, timeframe = '4H' }) {
  // Obsługa nowego formatu (timeframes) i starego (symbols)
  let patterns = [];
  let updated = classicData?.updated;

  if (classicData?.timeframes?.[timeframe]?.symbols?.[symbol]) {
    patterns = classicData.timeframes[timeframe].symbols[symbol] || [];
    updated = classicData.timeframes[timeframe].updated || updated;
  } else if (classicData?.symbols?.[symbol]) {
    patterns = classicData.symbols[symbol] || [];
  }

  patterns = patterns.slice(-30).reverse();

  const STATUS_ICONS = {
    'FORMUJĄCA SIĘ': '…',
    'POTWIERDZONA': '✓',
    'WYBITA': '▲',
    'RETEST': '↻',
    'UNIEWAŻNIONA': '✕',
    'WYGASŁA': '–',
  };

  return (
    <section className="border border-border rounded-xl bg-panel/60 p-4">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <h3 className="font-bold">Formacje klasyczne · {timeframe}</h3>
        <span className="text-xs text-muted">Aktualizacja: {updated || 'brak danych'}</span>
      </div>
      {!patterns.length ? (
        <p className="text-muted text-sm">Brak wykrytych formacji klasycznych w aktualnych danych.</p>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
          {patterns.map((pattern, index) => {
            const status = pattern.status || 'POTWIERDZONA';
            const dir = pattern.direction || 'neutral';
            const isBullish = dir === 'bullish';
            const nameLabel = NAMES[pattern.name || pattern.type] || (pattern.type || pattern.name || 'Formacja');
            const subtypeLabel = pattern.subtype ? SUBTYPE_LABELS[pattern.subtype] || pattern.subtype : '';
            return (
              <article
                key={pattern.id || `${pattern.time}-${pattern.name || pattern.type}-${index}`}
                className={`border border-border rounded-lg p-3 ${status === 'FORMUJĄCA SIĘ' ? 'bg-panel/40' : 'bg-panel2'}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-sm">{nameLabel}</div>
                  <span className={`text-xs font-bold ${STATUS_COLORS[status] || 'text-gray-400'}`}>
                    {STATUS_ICONS[status]} {STATUS_LABELS[status]}
                  </span>
                </div>
                {subtypeLabel ? (
                  <div className="text-xs text-muted mb-1">{subtypeLabel}</div>
                ) : null}
                <div className={`text-xs mt-1 ${isBullish ? 'text-green-400' : dir === 'bearish' ? 'text-red-400' : 'text-gray-400'}`}>
                  {isBullish ? 'Wzrostowa' : dir === 'bearish' ? 'Spadkowa' : 'Neutralna'} · {pattern.timeframe || timeframe}
                </div>
                <div className="text-xs text-muted mt-2">
                  Cena: {pattern.price ?? '—'} · {pattern.time || '—'}
                </div>
                {pattern.breakout_level != null ? (
                  <div className="text-xs text-xs mt-1 text-red-300/80">
                    Wybicie: {pattern.breakout_level}
                  </div>
                ) : null}
                {pattern.retest_level != null ? (
                  <div className="text-xs text-xs mt-1 text-purple-300/80">
                    Retest: {pattern.retest_level}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
