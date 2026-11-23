export default function Layout({ sidebar, main }) {
  return (
    <div className="flex flex-col md:flex-row h-screen overflow-hidden">
      <aside className="w-full md:w-80 border-r border-border bg-panel flex flex-col z-10">
        {sidebar}
      </aside>
      <main className="flex-1 overflow-y-auto bg-bg p-4 md:p-6">
        {main}
      </main>
    </div>
  );
}