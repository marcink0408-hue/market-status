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
  const updated = classicData?.updated;

  // classic_patterns.json jest nieaktualny (ostatnia aktualizacja: 2026-10-30).
  // Nie pokazuj jego wpisów jako bieżących formacji ani sygnałów.
  return (
    <div className="border border-border rounded-lg bg-panel2 p-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-semibold">📐 Formacje klasyczne</span>
      </div>
      <p className="text-muted text-sm">
        Dane historyczne niedostępne jako aktualne wykrycia (ostatnia aktualizacja: {updated ? new Date(updated).toLocaleDateString('pl-PL') : 'brak danych'}).
      </p>
    </div>
  );
}