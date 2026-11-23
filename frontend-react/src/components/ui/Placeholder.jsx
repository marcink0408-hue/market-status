export default function Placeholder({ message }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 border border-dashed border-border rounded-xl bg-panel/50 text-muted text-center">
      {message || 'Brak danych'}
    </div>
  );
}