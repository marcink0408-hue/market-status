export const TIMEFRAMES = ['1H', '4H', '1D'];

export function normalizeDecision(value) {
  const decision = String(value || '').toUpperCase();
  return ['LONG', 'SHORT'].includes(decision) ? decision : 'BRAK';
}

export function statusItems(status) {
  if (Array.isArray(status)) return status;
  return status?.decisions || status?.signals || status?.results || [];
}

export function timeframeData(instrument, timeframe) {
  return instrument?.timeframes?.[timeframe]
    || (timeframe === '1D' ? instrument?.timeframes?.Daily : null)
    || {};
}

function identityMatches(item, symbol, timeframe) {
  const itemSymbol = item?.symbol == null ? null : String(item.symbol).toLowerCase();
  const itemTimeframe = item?.timeframe === 'Daily' ? '1D' : item?.timeframe;
  return (itemSymbol == null || itemSymbol === symbol)
    && (itemTimeframe == null || itemTimeframe === timeframe);
}

function validCandles(candles) {
  const byTime = new Map();
  (Array.isArray(candles) ? candles : []).forEach((candle) => {
    const values = ['time', 'open', 'high', 'low', 'close'].map((key) => Number(candle[key]));
    if (!values.every(Number.isFinite) || values[0] <= 0) return;
    const [time, open, high, low, close] = values;
    if (high < Math.max(open, close, low) || low > Math.min(open, close, high)) return;
    byTime.set(time, { time, open, high, low, close });
  });
  return [...byTime.values()].sort((a, b) => a.time - b.time);
}

export function getChartPayload(ohlc, selectedSymbol, timeframe = '4H') {
  const symbol = String(selectedSymbol || '').toLowerCase();
  const container = ohlc?.symbols?.[symbol] || ohlc?.symbols?.[selectedSymbol];
  if (!symbol || !container) return null;

  const nested = container.timeframes?.[timeframe]
    || (timeframe === '1D' ? container.timeframes?.Daily : null);
  const isLegacy4H = timeframe === '4H' && Array.isArray(container.candles);
  const source = nested || (isLegacy4H ? container : null);
  if (!source || !identityMatches(source, symbol, timeframe)) return null;

  const candles = validCandles(source.candles);
  if (!candles.length) return null;
  const times = new Set(candles.map((candle) => candle.time));
  const markers = (source.markers || []).filter((marker) => (
    identityMatches(marker, symbol, timeframe) && times.has(Number(marker.time))
  ));
  const harmonics = (source.harmonics || [])
    .filter((pattern) => identityMatches(pattern, symbol, timeframe))
    .map((pattern) => ({
      ...pattern,
      symbol,
      timeframe,
      points: (pattern.points || [])
        .filter((point) => times.has(Number(point.time)) && Number.isFinite(Number(point.value)))
        .map((point) => ({ ...point, time: Number(point.time), value: Number(point.value) })),
    }))
    .filter((pattern) => pattern.points.length >= 2);

  return {
    ...source,
    symbol,
    timeframe,
    candles,
    markers,
    harmonics,
    levels: source.levels || {},
    levels_timeframe: source.levels_timeframe || timeframe,
  };
}

export function harmonicLinePoints(pattern) {
  const byTime = new Map();
  (pattern?.points || []).forEach((point) => {
    if (Number.isFinite(point.time) && Number.isFinite(point.value)) byTime.set(point.time, point);
  });
  return [...byTime.values()].sort((a, b) => a.time - b.time);
}

export function chartMarkers(payload) {
  const markers = [...(payload?.markers || [])];
  (payload?.harmonics || []).forEach((pattern) => {
    const bullish = pattern.direction === 'bullish';
    pattern.points.forEach((point) => markers.push({
      time: point.time,
      position: bullish ? 'belowBar' : 'aboveBar',
      color: bullish ? '#35d07f' : '#ff6376',
      shape: 'circle',
      text: `${pattern.name || 'H'} ${point.label || ''} · ${payload.timeframe}`,
    }));
  });
  return markers.sort((a, b) => Number(a.time) - Number(b.time));
}
