const CANDLE_DESC = {
  'bullish engulfing': ['🟩', 'Bullish Engulfing', 'Świeca wzrostowa obejmuje poprzednią.'],
  'bearish engulfing': ['🟥', 'Bearish Engulfing', 'Świeca spadkowa obejmuje poprzednią.'],
  hammer: ['🔨', 'Hammer', 'Mały korpus i długi dolny cień.'],
  doji: ['➕', 'Doji', 'Otwarcie i zamknięcie zbliżone.'],
};

const normalizeName = (s) => String(s || '').toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();

const lookupCandle = (name) => {
  const n = normalizeName(name);
  for (const [k, v] of Object.entries(CANDLE_DESC)) {
    if (normalizeName(k) === n || normalizeName(v[1]) === n) return v;
  }
  if (n.includes('engulfing')) return CANDLE_DESC[n.includes('bear') ? 'bearish engulfing' : 'bullish engulfing'];
  if (n.includes('doji')) return CANDLE_DESC.doji;
  if (n.includes('hammer')) return CANDLE_DESC.hammer;
  if (n.includes('morning star') || n.includes('evening star')) {
    return ['🌅', name.charAt(0).toUpperCase() + name.slice(1), 'Formacja gwiazdy — sygnał odwrócenia trendu.'];
  }
  if (n.includes('shooting star')) {
    return ['🌠', name.charAt(0).toUpperCase() + name.slice(1), 'Gwiazda strzelająca — sygnał spadkowy.'];
  }
  return null;
};

const CandleSvg = ({ name, direction = 'bullish' }) => {
  const n = normalizeName(name);
  const color = direction === 'bearish' ? '#ff6376' : '#35d07f';
  let bodies = [];

  if (n.includes('evening star') || n.includes('morning star')) {
    bodies = [
      [12, 14, 10, 24, color],
      [34, 23, 6, 6, '#94a3b8'],
      [55, 25, 10, 24, n.includes('evening') ? '#ff6376' : '#35d07f'],
    ];
  } else if (n.includes('engulfing')) {
    bodies = [
      [19, 24, 12, 24, n.includes('bearish') ? '#35d07f' : '#ff6376'],
      [39, 15, 18, 39, color],
    ];
  } else if (n.includes('hammer')) {
    bodies = [[31, 22, 15, 17, color]];
  } else {
    bodies = [
      [13, 22, 12, 27, '#35d07f'],
      [34, 15, 12, 30, '#ff6376'],
      [55, 24, 12, 20, color],
    ];
  }

  return (
    <svg viewBox="0 0 80 65" aria-hidden="true" className="w-16 h-16 mx-auto">
      <g stroke={color} strokeWidth="2" strokeLinecap="round">
        {bodies.map(([x, y, w, h, c]) => (
          <>
            <line x1={x + w / 2} y1={Math.max(4, y - 12)} x2={x + w / 2} y2={Math.min(61, y + h + 12)} stroke={c} />
            <rect x={x} y={y} width={w} height={Math.max(2, h)} rx="1" fill={c} stroke={c} />
          </>
        ))}
      </g>
    </svg>
  );
};

export default function CandlePatterns({ instrument }) {
  const tf = instrument?.timeframes?.['4H'] || {};
  const candles = tf.candles || [];

  if (!candles.length) {
    return (
      <div className="border border-border rounded-lg bg-panel2 p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold">🕯️ Formacje świecowe</span>
        </div>
        <p className="text-muted text-sm">Brak formacji świecowych.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold">🕯️ Formacje świecowe</span>
      </div>
      <div className="space-y-3">
        {candles.map((c, i) => {
          const desc = lookupCandle(c.name) || ['🕯️', c.name || 'Formacja', 'Wykryta formacja.'];
          const isBullish = c.direction === 'bullish';
          const isBearish = c.direction === 'bearish';
          return (
            <div key={i} className="border border-border rounded-lg bg-panel2 p-3">
              <div className="flex items-start justify-between gap-3 mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{desc[0]}</span>
                  <div className="text-sm font-bold">{desc[1]}</div>
                  {isBullish ? (
                    <span className="px-1.5 py-0.5 rounded text-xs border border-green-500/30 text-green-400 bg-green-500/10">
                      Wzrostowa
                    </span>
                  ) : isBearish ? (
                    <span className="px-1.5 py-0.5 rounded text-xs border border-red-500/30 text-red-400 bg-red-500/10">
                      Spadkowa
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded text-xs border border-border text-muted bg-panel2">
                      Neutralna
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-xs text-muted">{c.strength || ''}</div>
                  <div className="text-[0.6rem] text-muted">{c.time ? c.time.slice(0, 16) : '—'}</div>
                </div>
              </div>
              <p className="text-muted text-xs mb-2">{desc[2]}</p>
              <div className="flex items-center gap-2">
                <CandleSvg name={c.name} direction={c.direction} />
                <span className="text-xs text-muted ml-2">Diagram poglądowy formacji świecowej</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}