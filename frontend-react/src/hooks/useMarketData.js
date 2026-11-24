import { useState, useEffect, useCallback, useRef } from 'react';

const FILES = [
  'status',
  'ohlc',
  'decisions',
  'classic',
  'signals',
];

const FILENAMES = {
  status: 'status.json',
  ohlc: 'ohlc.json',
  decisions: 'decisions_log.json',
  classic: 'classic_patterns.json',
  signals: 'signals_history.json',
};

function jsonUrl(key) {
  const base = import.meta.env.BASE_URL || '/';
  const normalizedBase = base.endsWith('/') ? base : base + '/';
  return normalizedBase + 'output/' + FILENAMES[key];
}

const initialFileStatus = {};
FILES.forEach((key) => { initialFileStatus[key] = 'idle'; });

const initialData = {};
FILES.forEach((key) => { initialData[key] = null; });

export function useMarketData() {
  const [data, setData] = useState(initialData);
  const [fileStatus, setFileStatus] = useState({ ...initialFileStatus });
  const [overallStatus, setOverallStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const requestIdRef = useRef(0);

  const load = useCallback(async (isRefresh = false) => {
    const requestId = ++requestIdRef.current;
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setOverallStatus('loading');
      setError(null);
    }
    setFileStatus({ ...initialFileStatus });

    const results = { ...initialData };
    let requiredFailed = false;
    let requiredError = null;

    await Promise.all(FILES.map(async (key) => {
      try {
        setFileStatus((prev) => ({ ...prev, [key]: 'loading' }));
        const res = await fetch(jsonUrl(key) + '?v=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        results[key] = json;
        setFileStatus((prev) => ({ ...prev, [key]: 'success' }));
      } catch (err) {
        setFileStatus((prev) => ({ ...prev, [key]: 'error' }));
        if (key === 'status') {
          requiredFailed = true;
          requiredError = err.message;
        } else {
          results[key] = null;
        }
      }
    }));

    if (requestId !== requestIdRef.current) return;

    if (requiredFailed) {
      setOverallStatus('error');
      setError(requiredError || 'Nie udało się wczytać danych statusu.');
      if (isRefresh) setRefreshing(false);
      return;
    }

    setData(results);
    setOverallStatus('ready');
    if (isRefresh) setRefreshing(false);
  }, []);

  useEffect(() => {
    load();
    return () => { requestIdRef.current += 1; };
  }, [load]);

  const refresh = useCallback(() => {
    load(true);
  }, [load]);

  return {
    data,
    fileStatus,
    overallStatus,
    error,
    refreshing,
    refresh,
  };
}