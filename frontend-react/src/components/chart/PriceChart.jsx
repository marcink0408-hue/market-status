import { createChart, LineStyle } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

const CHART_LAYOUT = {
  background: { type: 'solid', color: '#080e17' },
  textColor: '#b8c7da',
};

const CHART_GRID = {
  vertLines: { color: '#172438' },
  horzLines: { color: '#172438' },
};

const CANDLE_SERIES_OPTIONS = {
  upColor: '#35d07f',
  downColor: '#ff6376',
  borderUpColor: '#35d07f',
  borderDownColor: '#ff6376',
  wickUpColor: '#35d07f',
  wickDownColor: '#ff6376',
};

const LEVEL_CONFIG = [
  { key: 'entry', title: 'WEJŚCIE', color: '#70b7ff' },
  { key: 'stop', title: 'STOP LOSS', color: '#ff6376' },
  { key: 'target', title: 'TAKE PROFIT', color: '#35d07f' },
];

export default function PriceChart({ candles, levels, harmonics }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const priceLinesRef = useRef({});
  const harmonicLinesRef = useRef([]);

  // --- Inicjalizacja wykresu przy montowaniu ---
  useEffect(() => {
    if (!containerRef.current) {
      console.error('PriceChart: brak kontenera DOM do inicjalizacji wykresu.');
      return;
    }

    const chartInstance = createChart(containerRef.current, {
      width: containerRef.current.clientWidth || 600,
      height: containerRef.current.clientHeight || 420,
      layout: CHART_LAYOUT,
      grid: CHART_GRID,
      rightPriceScale: { borderColor: '#2a3b53' },
      timeScale: { borderColor: '#2a3b53', timeVisible: true, secondsVisible: false },
    });

    const series = chartInstance.addCandlestickSeries(CANDLE_SERIES_OPTIONS);

    chartRef.current = { instance: chartInstance, series };

    if (candles && Array.isArray(candles) && candles.length) {
      series.setData(candles);
      chartInstance.timeScale().fitContent();
    }

    renderPriceLevels(series, levels);
    renderHarmonics(chartInstance, series, harmonics);

    const resizeObserver = new ResizeObserver((entries) => {
      if (chartInstance && entries[0]) {
        chartInstance.applyOptions({
          width: entries[0].contentRect.width,
        });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      removeAllPriceLevels();
      removeAllHarmonics(series);
      chartInstance.remove();
      chartRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Aktualizacja danych świec po zmianie instrumentu ---
  useEffect(() => {
    if (!chartRef.current) return;
    if (candles && Array.isArray(candles)) {
      chartRef.current.series.setMarkers([]);
      chartRef.current.series.setData(candles);
      if (candles.length) {
        chartRef.current.instance.timeScale().fitContent();
      }
    }
  }, [candles]);

  // --- Aktualizacja poziomów po zmianie instrumentu ---
  useEffect(() => {
    if (!chartRef.current) return;
    removeAllPriceLevels();
    renderPriceLevels(chartRef.current.series, levels);
  }, [levels]);

  // --- Aktualizacja markerów harmonicznych po zmianie instrumentu ---
  useEffect(() => {
    if (!chartRef.current) return;
    removeAllHarmonics(chartRef.current.series);
    renderHarmonics(chartRef.current.instance, chartRef.current.series, harmonics);
  }, [harmonics]);

  function renderPriceLevels(series, levels) {
    if (!series || !levels) return;
    LEVEL_CONFIG.forEach(({ key, title, color }) => {
      const v = levels[key];
      if (v != null && Number.isFinite(Number(v))) {
        priceLinesRef.current[key] = series.createPriceLine({
          price: Number(v),
          color,
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title,
        });
      }
    });
  }

  function removeAllPriceLevels() {
    Object.values(priceLinesRef.current).forEach((line) => {
      try {
        line.remove();
      } catch (e) {
        // ignore
      }
    });
    priceLinesRef.current = {};
  }

  function renderHarmonics(chartInstance, series, harmonics) {
    if (!chartInstance || !series || !harmonics) return;

    (harmonics || []).forEach((p) => {
      const pts = p.points || [];
      if (pts.length < 2) return;

      const validPoints = pts
        .filter((x) => x.time != null && x.value != null)
        .map((x) => ({ time: x.time, value: x.value }))
        .sort((a, b) => a.time - b.time);
      if (validPoints.length < 2) return;

      const isBullish = p.direction === 'bullish';
      const line = chartInstance.addLineSeries({
        color: isBullish ? '#35d07f' : '#ff6376',
        lineWidth: 2,
        lineStyle: p.status === 'completed' ? LineStyle.Solid : LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      line.setData(validPoints);

      const markers = [];
      for (const point of pts) {
        if (point.time == null) continue;
        markers.push({
          time: point.time,
          position: isBullish ? 'belowBar' : 'aboveBar',
          color: isBullish ? '#35d07f' : '#ff6376',
          shape: 'circle',
          text: `${p.name || 'H'} ${point.label || ''}`,
        });
      }

      if (markers.length) {
        series.setMarkers(markers);
      }

      harmonicLinesRef.current.push({ line, markers });
    });
  }

  function removeAllHarmonics(series) {
    harmonicLinesRef.current.forEach(({ line }) => {
      try {
        line.remove();
      } catch (e) {
        // ignore
      }
    });
    harmonicLinesRef.current = [];
    if (series) {
      series.setMarkers([]);
    }
  }

  return <div ref={containerRef} className="w-full h-full" />;
}
