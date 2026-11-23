export default function Sidebar({ children }) {
  return (
    <div className="flex flex-col h-full">
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
          <span className="px-3 py-1.5 rounded-full border border-border bg-panel2 text-xs text-muted">
            ● Ładowanie danych…
          </span>
          <button className="px-3 py-1.5 rounded-full border border-blue-500/50 bg-blue-900/30 text-blue-300 text-xs hover:border-blue-400 transition-colors">
            ↻ Odśwież
          </button>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto p-4">{children}</div>
    </div>
  );
}