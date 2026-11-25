function MarketLogo({ small = false }) {
  return (
    <svg viewBox="0 0 180 180" className={small ? 'h-10 w-10' : 'h-36 w-36 md:h-48 md:w-48'} aria-hidden="true">
      <defs>
        <linearGradient id="logo-red" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#ff493b" /><stop offset="1" stopColor="#a90f09" />
        </linearGradient>
        <filter id="logo-glow"><feGaussianBlur stdDeviation="4" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      <path d="M90 8 157 46v88l-67 38-67-38V46Z" fill="#181414" stroke="url(#logo-red)" strokeWidth="5" filter="url(#logo-glow)" />
      <path d="M42 113V67l48 52 48-52v46" fill="none" stroke="url(#logo-red)" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m48 132 27-24 21 13 36-42" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m122 79 10-1-1 11" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

function MarketIcon({ type }) {
  const paths = {
    chart: 'M4 17 9 11l4 3 7-9M16 5h4v4',
    coin: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-3 5h4a2 2 0 0 1 0 4h-3m0 0h4a2 2 0 0 1 0 4H9m3-12v2m0 8v2',
    candles: 'M6 4v3m0 8v5m-3-12h6v7H3Zm15-4v3m0 8v5m-3-12h6v7h-6Z',
    globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-9 9h18M12 3c3 3 3 15 0 18m0-18c-3 3-3 15 0 18',
  };
  return <svg viewBox="0 0 24 24" className="h-9 w-9" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[type]} /></svg>;
}

export default function WelcomeScreen({ onEnter }) {
  return (
    <main className="welcome-screen">
      <div className="welcome-grid" aria-hidden="true" />
      <button type="button" className="welcome-core group" onClick={onEnter} aria-label="Wejdź do panelu Market Status">
        <span className="welcome-orbit"><MarketLogo /></span>
        <span className="mt-5 text-xs font-bold uppercase tracking-[0.55em] text-[var(--brand-red-hover)]">Market Status</span>
        <span className="welcome-title">WITAJ MARCIN</span>
        <span className="mt-4 rounded-full border border-[var(--brand-red)]/50 bg-[var(--brand-red)]/10 px-6 py-2 text-xs font-bold uppercase tracking-[0.25em] text-white transition group-hover:bg-[var(--brand-red)] group-hover:shadow-[var(--glow-red)]">Wejdź na rynek</span>
      </button>
      <div className="welcome-side welcome-side-left" aria-hidden="true">
        <div className="welcome-icon"><MarketIcon type="chart" /><span>TREND</span></div>
        <div className="welcome-icon"><MarketIcon type="candles" /><span>ŚWIECE</span></div>
      </div>
      <div className="welcome-side welcome-side-right" aria-hidden="true">
        <div className="welcome-icon"><MarketIcon type="coin" /><span>CFD</span></div>
        <div className="welcome-icon"><MarketIcon type="globe" /><span>RYNEK</span></div>
      </div>
      <p className="absolute bottom-6 px-6 text-center text-[0.65rem] uppercase tracking-[0.25em] text-[var(--text-muted)]">Analiza 1H · 4H · 1D <span className="text-[var(--brand-red)]">•</span> jeden panel decyzyjny</p>
    </main>
  );
}
