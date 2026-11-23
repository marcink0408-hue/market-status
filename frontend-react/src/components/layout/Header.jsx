export default function Header({ overallStatus, error, refreshing, refresh }) {
  const statusVariants = {
    loading: { color: 'text-muted', label: 'Ładowanie danych…' },
    ready: { color: 'text-green-400', label: 'Dane załadowane' },
    error: { color: 'text-red-400', label: 'Błąd danych' },
  };
  const v = statusVariants[overallStatus] || statusVariants.loading;

  return (
    <header className="flex items-center justify-between gap-4 px-4 py-3 border-b border-border bg-panel/80 backdrop-blur sticky top-0 z-20 flex-wrap">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-green-400 flex items-center justify-center text-black font-black text-xl">
          M
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">Market Status <span className="text-blue-400">·</span> Analiza 4H</h1>
          <p className="text-xs text-muted">Sygnały, formacje i statystyki rynku w jednym miejscu</p>
        </div>
      </div>
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`px-3 py-1.5 rounded-full border border-border bg-panel2 text-xs ${v.color}`}>
          {error && overallStatus === 'error' ? `● Błąd: ${error}` : v.label}
        </span>
        <button
          className="px-3 py-1.5 rounded-full border border-blue-500/50 bg-blue-900/30 text-blue-300 text-xs hover:border-blue-400 transition-colors"
          onClick={refresh}
          disabled={refreshing}
          aria-label="Odśwież dane"
        >
          {refreshing ? '↻ Odświeżanie…' : '↻ Odśwież'}
        </button>
      </div>
    </header>
  );
}