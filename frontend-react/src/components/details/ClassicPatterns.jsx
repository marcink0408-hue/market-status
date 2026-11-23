const CLASSIC_DESC = {
  double_top: ['⛰️', 'Podwójny szczyt', 'Dwa podobne szczyty.'],
  double_bottom: ['🏞️', 'Podwójne dno', 'Dwa podobne dołki.'],
  head_and_shoulders: ['🗻', 'Głowa z ramionami', 'Trzy szczyty, środkowy najwyższy.'],
};

const normalizeName = (s) => String(s || '').toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();

const lookupClassic = (name) => {
  const n = normalizeName(name);
  for (const [k, v] of Object.entries(CLASSIC_DESC)) {
    if (normalizeName(k) === n || normalizeName(v[1]) === n) return v;
  }
  if (n.includes('double top')) return CLASSIC_DESC.double_top;
  if (n.includes('double bottom')) return CLASSIC_DESC.double_bottom;
  if (n.includes('head') || n.includes('shoulders')) return CLASSIC_DESC.head_and_shoulders;
  return null;
};

const ClassicSvg = ({ name }) => {
  const n = normalizeName(name);
  let pts = '5,48 20,15 34,44 49,15 64,48 75,30';
  if (n.includes('double top')) pts = '5,48 20,14 35,45 53,15 75,48';
  else if (n.includes('double bottom')) pts = '5,15 20,48 35,20 53,48 75,15';
  else if (n.includes('head')) pts = '4,47 18,25 28,39 41,8 54,39 64,25 76,47';

  return (
    <svg viewBox="0 0 80 65" aria-hidden="true" className="w-16 h-16 mx-auto">
      <polyline points={pts} fill="none" stroke="#70b7ff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

export default function ClassicPatterns({ classicData, symbol }) {
  const symbols = classicData?.symbols || {};
  const classics = symbols[symbol] || [];

  if (!classics.length) {
    return (
      <div className="border border-border rounded-lg bg-panel2 p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold">📐 Formacje klasyczne</span>
        </div>
        <p className="text-muted text-sm">Brak klasycznych formacji.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold">📐 Formacje klasyczne</span>
      </div>
      <div className="space-y-3">
        {classics.slice(-30).reverse().map((c, i) => {
          const desc = lookupClassic(c.name) || ['📊', c.name || 'Formacja', 'Wykryta formacja.'];
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
                      Wykryta
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono">{c.price != null ? c.price.toFixed?.(2) ?? c.price : '—'}</div>
                  <div className="text-[0.6rem] text-muted">{c.time ? c.time.slice(0, 16) : '—'}</div>
                </div>
              </div>
              <p className="text-muted text-xs mb-2">{desc[2]}</p>
              <div className="flex items-center gap-2">
                <ClassicSvg name={c.name} />
                <span className="text-xs text-muted ml-2">Schemat formacji klasycznej</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}