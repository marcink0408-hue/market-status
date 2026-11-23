import { useState } from 'react';
import Header from './components/layout/Header';
import InstrumentPanel from './components/instruments/InstrumentPanel';
import MainWorkspace from './components/workspace/MainWorkspace';
import Layout from './components/layout/Layout';
import { useMarketData } from './hooks/useMarketData';

export default function App() {
  const [activeInstrument, setActiveInstrument] = useState(null);
  const { data, overallStatus, error, refreshing, refresh } = useMarketData();

  return (
    <div className="min-h-screen bg-bg text-text">
      <Layout
        sidebar={
          <>
            <Header
              overallStatus={overallStatus}
              error={error}
              refreshing={refreshing}
              refresh={refresh}
            />
            <InstrumentPanel onSelect={setActiveInstrument} />
          </>
        }
        main={
          <>
            <MainWorkspace activeInstrument={activeInstrument} data={data} />
          </>
        }
      />
    </div>
  );
}