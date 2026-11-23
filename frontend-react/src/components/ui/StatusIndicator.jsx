export default function StatusIndicator({ status = 'loading' }) {
  const variants = {
    loading: { color: 'text-muted', label: 'Ładowanie danych…' },
    ready: { color: 'text-green-400', label: 'Dane załadowane' },
    error: { color: 'text-red-400', label: 'Błąd danych' },
  };
  const v = variants[status] || variants.loading;
  return (
    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-panel2 text-xs">
      <span className="w-1.5 h-1.5 rounded-full bg-current" style={{ color: 'inherit' }} aria-hidden="true" />
      {v.label}
    </span>
  );
}