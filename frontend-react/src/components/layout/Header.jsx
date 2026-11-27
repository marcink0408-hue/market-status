import { formatSymbolName } from '../../utils/market';

function RefreshIcon({ spinning }) {
  return <svg viewBox="0 0 24 24" className={`h-5 w-5 ${spinning ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 6v5h-5M4 18v-5h5" /><path d="M6.1 9A7 7 0 0 1 18 6l2 5M4 13l2 5a7 7 0 0 0 11.9-3" /></svg>;
}

export default function Header({ overallStatus, error, refreshing, refresh, ohlc, selectedSymbol, selectedTimeframe }) {
  const generated = Date.parse(ohlc?.generated_at || '');
  const age = Date.now() - generated;
  const fresh = overallStatus === 'ready' && Number.isFinite(generated) && age >= -300000 && age <= 36 * 3600000;
  const status = refreshing
    ? { label: 'SYNC', className: 'status-wait' }
    : overallStatus === 'error'
      ? { label: 'BŁĄD', className: 'status-error' }
      : fresh
        ? { label: 'GO', className: 'status-go' }
        : overallStatus === 'loading'
          ? { label: 'ŁADOWANIE', className: 'status-wait' }
          : { label: generated ? 'NIEAKTUALNE' : 'BRAK DANYCH', className: 'status-error' };

  const symbolName = selectedSymbol ? formatSymbolName(selectedSymbol) : null;
  const timeframeLabel = selectedTimeframe || '4H';

  return (
    <header className="main-header">
      <div className="flex items-center gap-3">
        <div className="header-mark" aria-hidden="true">M</div>
        <span className="hidden text-[0.65rem] font-bold uppercase tracking-[0.25em] text-[var(--text-muted)] sm:block">Trading<br />Dashboard</span>
      </div>
      <h1 className="main-title">
        MARCIN <span>–</span> MÓJ XTB
        {symbolName && timeframeLabel ? (
          <span className="text-[var(--text-muted)] font-normal ml-2 tracking-normal whitespace-nowrap">| {symbolName} | {timeframeLabel}</span>
        ) : null}
      </h1>
      <div className="flex items-center justify-end gap-2 md:gap-3">
        <span className={`status-tile ${status.className}`} title={error || (fresh ? 'Dane są aktualne' : 'Dane wymagają odświeżenia')}>{status.label}</span>
        <button className="refresh-button" type="button" onClick={refresh} disabled={refreshing} aria-label="Odśwież dane">
          <RefreshIcon spinning={refreshing} /><span>{refreshing ? 'POBIERAM' : 'ODŚWIEŻ'}</span>
        </button>
      </div>
      {error && <p className="col-span-full text-center text-xs text-red-300" role="alert">{error}</p>}
    </header>
  );
}
