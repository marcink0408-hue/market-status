import { createChart, LineStyle } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import { chartMarkers, getPricePrecision, formatPrice, harmonicLinePoints } from '../../utils/market';

function classicColor(direction) {
  return direction === 'bullish' ? '#35d07f' : direction === 'bearish' ? '#ff4d42' : '#bb86fc';
}

function statusLineStyle(status) {
  switch (status) {
    case 'FORMUJĄCA SIĘ': return LineStyle.Dashed;
    case 'UNIEWAŻNIONA': return LineStyle.Dotted;
    case 'WYGASŁA': return LineStyle.Dotted;
    default: return LineStyle.Solid;
  }
}

function statusColor(direction, status) {
  const base = classicColor(direction);
  switch (status) {
    case 'FORMUJĄCA SIĘ': return base + 'B3'; // ~70% opacity
    case 'UNIEWAŻNIONA': return base + '59';  // ~35% opacity
    case 'WYGASŁA': return base + '40';      // ~25% opacity
    default: return base;
  }
}

function finitePoints(points) {
  return (points || [])
    .map((p) => ({ time: Number(p?.time), value: Number(p?.value) }))
    .filter((p) => Number.isFinite(p.time) && Number.isFinite(p.value) && p.time > 0);
}

const LEVEL_CONFIG = [
  { key: 'entry', title: 'WEJŚCIE', color: '#70b7ff' },
  { key: 'stop', title: 'STOP LOSS', color: '#ff6376' },
  { key: 'target', title: 'TAKE PROFIT', color: '#35d07f' },
];

function toFiniteNumber(value) {
  if (
    value === null ||
    value === undefined ||
    (typeof value === 'string' && value.trim() === '')
  ) {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export default function PriceChart({ payload }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !payload?.candles?.length) return undefined;

    const pricePrecision = getPricePrecision(payload.symbol);

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth || 600,
      height: containerRef.current.clientHeight || 480,
      layout: { background: { type: 'solid', color: '#100d0d' }, textColor: '#b8b2b2' },
      localization: {
        priceFormatter: (price) =>
          price.toLocaleString('pl-PL', { maximumFractionDigits: pricePrecision }),
      },
      grid: { vertLines: { color: '#2a1919' }, horzLines: { color: '#2a1919' } },
      rightPriceScale: { borderColor: '#4a2725' },
      timeScale: { borderColor: '#4a2725', timeVisible: true, secondsVisible: false },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#35d07f', downColor: '#ff6376',
      borderUpColor: '#35d07f', borderDownColor: '#ff6376',
      wickUpColor: '#35d07f', wickDownColor: '#ff4d42',
      priceFormat: { type: 'price', precision: pricePrecision, minMove: pricePrecision === 2 ? 0.01 : 1 },
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

    // --- Strefy S/R: wsparcie (zielone) i opór (czerwone), bez rozszerzania autoskali ---
    const SR_CONFIG = [
      { type: 'SUPPORT', color: '#35d07f', titlePrefix: 'WSPARCIE' },
      { type: 'RESISTANCE', color: '#ff6376', titlePrefix: 'OPÓR' },
    ];

    // 1. Cena referencyjna
    let effectivePrice = toFiniteNumber(payload.sr_zones_current_price);
    if (effectivePrice == null && payload.candles?.length) {
      const lastCandle = payload.candles[payload.candles.length - 1];
      effectivePrice = toFiniteNumber(lastCandle.close);
    }

    // Jeśli brak ceny referencyjnej — nie wyświetlaj żadnych stref
    if (effectivePrice != null) {
      const zones = (payload.sr_zones || [])
        .map((zone) => {
          const cfg = SR_CONFIG.find((c) => c.type === zone.type);
          if (!cfg) return null;
          return {
            ...zone,
            color: cfg.color,
            titlePrefix: cfg.titlePrefix,
            center: toFiniteNumber(zone.center),
            lower: toFiniteNumber(zone.lower),
            upper: toFiniteNumber(zone.upper),
            rank_score: toFiniteNumber(zone.rank_score),
            rank_position: toFiniteNumber(zone.rank_position),
            distance_from_price: toFiniteNumber(zone.distance_from_price),
          };
        })
        .filter(Boolean)
        .filter((z) => z.center != null && z.lower != null && z.upper != null);

      // 2. Podział na dwie grupy i ranking osobno dla każdej
      const above = zones.filter((z) => z.center > effectivePrice);
      const below = zones.filter((z) => z.center < effectivePrice);

      const rankGroup = (group) => {
        const hasScore = group.every((z) => z.rank_score != null);
        const hasPosition = group.every((z) => z.rank_position != null);
        const hasDistance = group.every((z) => z.distance_from_price != null);

        return [...group].sort((a, b) => {
          if (hasScore) {
            if (b.rank_score !== a.rank_score) return b.rank_score - a.rank_score;
            return a.center - b.center;
          }
          if (hasPosition) {
            if (a.rank_position !== b.rank_position) return a.rank_position - b.rank_position;
            return a.center - b.center;
          }
          if (hasDistance) {
            if (a.distance_from_price !== b.distance_from_price) return a.distance_from_price - b.distance_from_price;
            return a.center - b.center;
          }
          return a.center - b.center;
        });
      };

      const selectedAbove = rankGroup(above).slice(0, 2);
      const selectedBelow = rankGroup(below).slice(0, 2);
      const selected = [...selectedAbove, ...selectedBelow];

      // 3. Render: jedna linia na center, etykieta z formatowanym zakresem
      selected.forEach((zone) => {
        candleSeries.createPriceLine({
          price: zone.center,
          color: zone.color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `${zone.titlePrefix} · ${formatPrice(zone.lower, payload.symbol)} – ${formatPrice(zone.upper, payload.symbol)}`,
        });
      });
    }

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

    // --- Formacje klasyczne: linie trendu, granice, wybicie i retest ---
    (payload.classic_patterns || []).forEach((pattern) => {
      const status = pattern.status || 'POTWIERDZONA';
      const color = statusColor(pattern.direction, status);
      const lineStyle = statusLineStyle(status);

      // Linie trendu (opór / wsparcie / neckline) — rysowane tylko dla ≥2 poprawnych punktów
      pattern.trendlines?.forEach((tl) => {
        const pts = finitePoints(tl.points);
        if (pts.length < 2) return;
        const line = chart.addLineSeries({
          color,
          lineWidth: 1,
          lineStyle,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
          autoscaleInfoProvider: () => null,
        });
        line.setData(pts);
        overlaySeries.push(line);
      });

      // Linie graniczne (poziome upper / lower)
      const boundary = pattern.boundary || {};
      [boundary.upper, boundary.lower].forEach((price) => {
        const p = toFiniteNumber(price);
        if (p == null) return;
        candleSeries.createPriceLine({
          price: p,
          color,
          lineWidth: 1,
          lineStyle,
          axisLabelVisible: false,
          title: `Formacja ${pattern.type || pattern.name} · ${status}`,
        });
      });

      // Poziom wybicia — tylko dla WYBITA i RETEST, nigdy dla FORMUJĄCA SIĘ
      if (status !== 'FORMUJĄCA SIĘ' && (status === 'WYBITA' || status === 'RETEST')) {
        const breakout = toFiniteNumber(pattern.breakout_level);
        if (breakout != null) {
          candleSeries.createPriceLine({
            price: breakout,
            color,
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: `Wybicie · ${formatPrice(breakout, payload.symbol)}`,
          });
        }
      }

      // Poziom retestu — tylko dla RETEST, nigdy dla FORMUJĄCA SIĘ
      if (status === 'RETEST') {
        const retest = toFiniteNumber(pattern.retest_level);
        if (retest != null) {
          candleSeries.createPriceLine({
            price: retest,
            color,
            lineWidth: 2,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `RETEST · ${formatPrice(retest, payload.symbol)}`,
          });
        }
      }
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
