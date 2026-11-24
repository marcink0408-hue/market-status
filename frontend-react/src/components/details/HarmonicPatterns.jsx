const HARMONIC_DESC = {
  gartley: ['🦋', 'Gartley', 'Klasyczna formacja harmoniczna XABCD.'],
  bat: ['🦇', 'Bat', 'Formacja harmoniczna oparta na proporcjach Fibonacciego.'],
  butterfly: ['🦋', 'Butterfly', 'Formacja harmoniczna z punktem D poza punktem X.'],
  crab: ['🦀', 'Crab', 'Formacja harmoniczna z wydłużonym ruchem.'],
  deepcrab: ['🦀', 'Deep Crab', 'Odmiana formacji Crab.'],
};

const normalizeName = (s) => String(s || '').toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();

const lookupHarmonic = (name) => {
  const n = normalizeName(name);
  for (const [k, v] of Object.entries(HARMONIC_DESC)) {
    if (normalizeName(k) === n || normalizeName(v[1]) === n) return v;
  }
  if (n.includes('butterfly')) return HARMONIC_DESC.butterfly;
  if (n.includes('gartley')) return HARMONIC_DESC.gartley;
  if (n.includes('crab')) return HARMONIC_DESC.crab;
  if (n.includes('bat')) return HARMONIC_DESC.bat;
  return null;
};

const HarmonicSvg = () => (
  <svg viewBox="0 0 80 65" aria-hidden="true" className="w-16 h-16 mx-auto">
    <polyline points="5,13 23,50 39,27 55,43 73,12" fill="none" stroke="#70b7ff" strokeWidth="2.5" strokeLinejoin="round" />
    <g fill="#f7c66b" stroke="#0b1320" strokeWidth="1.5">
      <circle cx="5" cy="13" r="4" />
      <circle cx="23" cy="50" r="4" />
      <circle cx="39" cy="27" r="4" />
      <circle cx="55" cy="43" r="4" />
      <circle cx="73" cy="12" r="4" />
    </g>
  </svg>
);

const lastKnownTime = (h) => h.time_C || h.time_B || h.time_A || h.time_X;

const harmonicDupKey = (h) =>
  `${h.name}|${h.direction}|${h.status}|${h.X}|${h.A}|${h.B}|${h.C}|${h.D !== undefined ? h.D : h.D_projected}|${lastKnownTime(h)}`;

export default function HarmonicPatterns({ instrument }) {
  const tf = instrument?.timeframes?.['4H'] || {};
  const harmonics = tf.harmonics || [];

  // Pokazuj wyłącznie formacje w trakcie (forming). Zakonczone (completed) wyklucz z prezentacji bieżących okazji.
  const forming = harmonics.filter((h) => h.status === 'forming');

  // Usuń rzeczywiste duplikaty (porównaj wszystkie kluczowe pola, nie scalaj na podstawie podobnych nazw).
  const seen = new Set();
  const unique = forming.filter((h) => {
    const key = harmonicDupKey(h);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Sortuj malejąco według czasu ostatniego znanego punktu.
  unique.sort((a, b) => new Date(lastKnownTime(b)) - new Date(lastKnownTime(a)));

  if (!unique.length) {
    return (
      <div className="border border-border rounded-lg bg-panel2 p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold">🦋 Formacje harmoniczne</span>
        </div>
        <p className="text-muted text-sm">Brak aktywnych formacji harmonicznych.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold">🦋 Formacje harmoniczne</span>
      </div>
      <div className="space-y-3">
        {unique.map((h, i) => {
          const desc = lookupHarmonic(h.name) || [h.direction === 'bullish' ? '🟢' : '🔴', h.name || 'Formacja', 'Formacja w trakcie wykształcania się.'];
          const isBullish = h.direction === 'bullish';
          const dVal = h.D !== undefined ? h.D : h.D_projected;
          const dLabel = h.D !== undefined ? 'D' : 'D (proj.)';
          return (
            <div key={i} className="border border-border rounded-lg bg-panel2 p-3">
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{desc[0]}</span>
                    <div className="text-sm font-bold">{desc[1]}</div>
                    <span className={`px-1.5 py-0.5 rounded text-xs border ${
                      isBullish ? 'border-green-500/30 text-green-400 bg-green-500/10' : 'border-red-500/30 text-red-400 bg-red-500/10'
                    }`}>
                      {h.direction === 'bullish' ? 'Wzrostowa' : 'Spadkowa'}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-xs border border-amber-500/30 text-amber-400 bg-amber-500/10">
                      W trakcie
                    </span>
                  </div>
                  <p className="text-muted text-xs mt-1">{desc[2]}</p>
                </div>
                <div className="text-right">
                  {h.error != null && (
                    <div className="text-xs text-muted">Błąd: {Number(h.error).toFixed(3)}</div>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2 mb-2">
                {['X', 'A', 'B', 'C', dLabel].map((point, idx) => {
                  const key = point === dLabel ? (h.D !== undefined ? 'D' : 'D_projected') : point;
                  const val = h[key];
                  const timeKey = `time_${point.toLowerCase() === 'd (proj.)' ? 'd' : point.toLowerCase()}`;
                  const timeVal = h[timeKey];
                  return (
                    <div key={idx} className="text-center">
                      <div className="text-[0.65rem] text-muted">{point}</div>
                      <div className="text-xs font-mono">{val != null ? val.toFixed?.(2) ?? val : '—'}</div>
                      <div className="text-[0.6rem] text-muted">{timeVal ? timeVal.slice(0, 10) : '—'}</div>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-2">
                <HarmonicSvg />
                <span className="text-xs text-muted ml-2">Schemat XABCD — punkty formacji harmonicznej</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}