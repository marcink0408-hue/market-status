import { createChart, LineStyle } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import { chartMarkers, harmonicLinePoints } from '../../utils/market';

const LEVEL_CONFIG = [
  { key: 'entry', title: 'WEJŚCIE', color: '#70b7ff' },
  { key: 'stop', title: 'STOP LOSS', color: '#ff6376' },
  { key: 'target', title: 'TAKE PROFIT', color: '#35d07f' },
];

export default function PriceChart({ payload }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !payload?.candles?.length) return undefined;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth || 600,
      height: containerRef.current.clientHeight || 480,
      layout: { background: { type: 'solid', color: '#100d0d' }, textColor: '#b8b2b2' },
      localization: { priceFormatter: (price) => Math.round(price).toLocaleString('pl-PL', { maximumFractionDigits: 0 }) },
      grid: { vertLines: { color: '#2a1919' }, horzLines: { color: '#2a1919' } },
      rightPriceScale: { borderColor: '#4a2725' },
      timeScale: { borderColor: '#4a2725', timeVisible: true, secondsVisible: false },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#35d07f', downColor: '#ff6376',
      borderUpColor: '#35d07f', borderDownColor: '#ff6376',
      wickUpColor: '#35d07f', wickDownColor: '#ff4d42',
      priceFormat: { type: 'price', precision: 0, minMove: 1 },
    });
    const overlaySeries = [];

    candleSeries.setData(payload.candles);
    candleSeries.setMarkers(chartMarkers(payload));

    LEVEL_CONFIG.forEach(({ key, title, color }) => {
      const value = Number(payload.levels?.[key]);
      if (payload.levels?.[key] != null && Number.isFinite(value)) {
        candleSeries.createPriceLine({
          price: value, color, lineWidth: 1, lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `${title} · ${payload.levels_timeframe || payload.timeframe}`,
        });
      }
    });

    payload.harmonics.forEach((pattern) => {
      const points = harmonicLinePoints(pattern);
      if (points.length < 2) return;
      const line = chart.addLineSeries({
        color: pattern.direction === 'bullish' ? '#35d07f' : '#ff4d42',
        lineWidth: 2,
        lineStyle: pattern.status === 'completed' ? LineStyle.Solid : LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        autoscaleInfoProvider: () => null,
      });
      line.setData(points);
      overlaySeries.push(line);
    });

    chart.timeScale().fitContent();
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) chart.applyOptions({ width: entries[0].contentRect.width });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      candleSeries.setMarkers([]);
      overlaySeries.forEach((series) => chart.removeSeries(series));
      chart.remove();
    };
  }, [payload]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      data-chart-identity={`${payload?.symbol || 'none'}:${payload?.timeframe || 'none'}`}
    />
  );
}
