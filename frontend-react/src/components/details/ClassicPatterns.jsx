const NAMES = {
  double_top: 'Podwójny szczyt', double_bottom: 'Podwójne dno',
  head_and_shoulders: 'Głowa z ramionami',
};

export default function ClassicPatterns({ classicData, symbol }) {
  const patterns = (classicData?.symbols?.[symbol] || []).slice(-30).reverse();
  return (
    <section className="border border-border rounded-xl bg-panel/60 p-4">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <h3 className="font-bold">Formacje klasyczne · 4H</h3>
        <span className="text-xs text-muted">Aktualizacja: {classicData?.updated || 'brak danych'}</span>
      </div>
      {!patterns.length ? (
        <p className="text-muted text-sm">Brak wykrytych formacji klasycznych w aktualnych danych.</p>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
          {patterns.map((pattern, index) => (
            <article key={`${pattern.time}-${pattern.name}-${index}`} className="border border-border rounded-lg bg-panel2 p-3">
              <div className="font-semibold">{NAMES[pattern.name] || pattern.name}</div>
              <div className={`text-xs mt-1 ${pattern.direction === 'bullish' ? 'text-green-400' : 'text-red-400'}`}>
                {pattern.direction === 'bullish' ? 'Wzrostowa' : 'Spadkowa'} · 4H
              </div>
              <div className="text-xs text-muted mt-2">Cena: {pattern.price ?? '—'} · {pattern.time || '—'}</div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
