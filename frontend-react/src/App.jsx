import { useEffect, useState } from 'react';
import Header from './components/layout/Header';
import WelcomeScreen from './components/layout/WelcomeScreen';
import InstrumentPanel from './components/instruments/InstrumentPanel';
import MainWorkspace from './components/workspace/MainWorkspace';
import { useMarketData } from './hooks/useMarketData';
import { statusItems } from './utils/market';

export default function App() {
  const [activeInstrument, setActiveInstrument] = useState(null);
  const [welcome, setWelcome] = useState(true);
  const { data, overallStatus, error, refreshing, refresh } = useMarketData();

  useEffect(() => {
    if (!activeInstrument && overallStatus === 'ready') {
      const first = statusItems(data.status)[0];
      if (first) setActiveInstrument(first);
    }
  }, [activeInstrument, data.status, overallStatus]);

  if (welcome) return <WelcomeScreen onEnter={() => setWelcome(false)} />;

  return (
    <div className="app-shell min-h-screen text-text">
      <Header overallStatus={overallStatus} error={error} refreshing={refreshing} refresh={refresh} ohlc={data.ohlc} />
      <main className="dashboard-enter w-full max-w-[1800px] mx-auto p-4 md:p-6 space-y-8">
        <InstrumentPanel
          data={data}
          overallStatus={overallStatus}
          error={error}
          activeSymbol={activeInstrument?.symbol}
          onSelect={setActiveInstrument}
        />
        <MainWorkspace activeInstrument={activeInstrument} data={data} />
      </main>
    </div>
  );
}
