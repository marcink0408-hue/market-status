export const TIMEFRAMES = ['1H', '4H', '1D'];

const SYMBOL_DISPLAY_NAMES = {
  w20: 'WIG20',
  us500: 'US500',
  gold: 'GOLD',
  silver: 'SILVER',
  eurpln: 'EUR/PLN',
  eurusd: 'EUR/USD',
  usdpln: 'USD/PLN',
  usdjpy: 'USD/JPY',
  copper: 'COPPER',
  eu50: 'EU50',
  uk100: 'UK100',
};

export function formatSymbolName(symbol) {
  if (!symbol) return '—';
  const key = String(symbol).toLowerCase();
  return SYMBOL_DISPLAY_NAMES[key] || String(symbol).toUpperCase();
}

export function currentDecision(instrument) {
  const terminal = ['STOP_LOSS', 'TAKE_PROFIT', 'EXPIRED', 'INVALIDATED', 'NO_DATA'];
  if (terminal.includes(instrument?.signal_status)) return 'BRAK';
  // Zgodność wsteczna: stary JSON nie może pokazywać historycznej harmonicznej jako setupu.
  if (!instrument?.signal_status && ['historical', 'invalidated', 'target_reached', 'expired'].includes(instrument?.harmonic?.lifecycle)) return 'BRAK';
  return normalizeDecision(instrument?.decision);
}

const FOREX_PRECISION_SYMBOLS = ['eurusd', 'usdpln', 'eurpln', 'usdjpy', 'copper'];

export function getPricePrecision(symbol) {
  if (!symbol) return 0;
  return FOREX_PRECISION_SYMBOLS.includes(String(symbol).toLowerCase()) ? 2 : 0;
}

export function formatPrice(value, symbol) {
  if (value == null || value === '' || !Number.isFinite(Number(value))) return '—';
  return Number(value).toLocaleString('pl-PL', { maximumFractionDigits: getPricePrecision(symbol) });
}

export function formatDate(value, includeTime = false) {
  const date = new Date(value);
  if (!value || !Number.isFinite(date.getTime())) return '—';
  return date.toLocaleString('pl-PL', includeTime
    ? { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: '2-digit', year: 'numeric' });
}

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

function findInstrumentInStatus(statusData, symbol) {
  if (!Array.isArray(statusData)) return null;
  const key = String(symbol).toLowerCase();
  return statusData.find((item) => String(item?.symbol).toLowerCase() === key) || null;
}

function candlePatternMarkers(statusData, symbol, timeframe, times) {
  const instrument = findInstrumentInStatus(statusData, symbol);
  if (!instrument) return [];

  const tfKey = timeframe === '1D' ? '1D' : timeframe;
  const tfData = instrument.timeframes?.[tfKey]
    || (timeframe === '1D' ? instrument.timeframes?.Daily : null)
    || {};
  const patterns = Array.isArray(tfData.candles) ? tfData.candles : [];

  const markers = [];
  const seenTimes = new Set();

  patterns.forEach((p) => {
    const t = Number(new Date(String(p.time || '').replace(' ', 'T')));
    if (!Number.isFinite(t)) return;
    const tSec = Math.floor(t / 1000);
    if (!times.has(tSec)) return;
    if (seenTimes.has(tSec)) return;
    seenTimes.add(tSec);

    const dir = String(p.direction || '').toLowerCase();
    let position, color;
    if (dir === 'bullish') { position = 'belowBar'; color = '#35d07f'; }
    else if (dir === 'bearish') { position = 'aboveBar'; color = '#ff4d42'; }
    else { position = 'belowBar'; color = '#94a3b8'; }

    const shortName = String(p.name || 'Formacja')
      .replace('Bullish ', '')
      .replace('Bearish ', '')
      .replace(' engulfing', '')
      .trim();

    markers.push({
      time: tSec,
      position,
      color,
      shape: 'circle',
      text: `${shortName} · ${dir || 'neutral'}`,
    });
  });

  return markers;
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

export function getChartPayload(ohlc, statusData, selectedSymbol, timeframe = '4H') {
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
  const ohlcMarkers = (source.markers || []).filter((marker) => (
    identityMatches(marker, symbol, timeframe) && times.has(Number(marker.time)) && marker.shape !== 'circle'
  ));
  const patternMarkers = candlePatternMarkers(statusData, symbol, timeframe, times);
  const markers = [...ohlcMarkers, ...patternMarkers];
  const lastTime = Math.max(...candles.map((candle) => candle.time));
  const harmonics = (source.harmonics || [])
    .filter((pattern) => {
      if (!identityMatches(pattern, symbol, timeframe)) return false;
      if (['forming', 'active'].includes(pattern.lifecycle) || !pattern.lifecycle) return true;
      const ended = Date.parse(pattern.closed_at || pattern.created_at || '') / 1000;
      return Number.isFinite(ended) && ended <= lastTime && lastTime - ended <= 5 * 86400;
    })
    .map((pattern) => ({
      ...pattern,
      symbol,
      timeframe,
      points: (pattern.points || [])
        .filter((point) => times.has(Number(point.time)) && Number.isFinite(Number(point.value)))
        .map((point) => ({ ...point, time: Number(point.time), value: Number(point.value) })),
    }))
    .filter((pattern) => pattern.points.length >= 2);

  const terminal = ['STOP_LOSS', 'TAKE_PROFIT', 'EXPIRED', 'INVALIDATED', 'NO_DATA'];
  const legacyHistoricalLevels = !source.signal_status && source.harmonics?.length > 0 && harmonics.length === 0;

  let levels;
  let effectiveLevelsTimeframe;

  if (timeframe === '4H') {
    // 4H: poziomy zawsze z bieżącego interwału (źródło prawdy)
    levels = terminal.includes(source.signal_status) || legacyHistoricalLevels ? {} : (source.levels || {});
    effectiveLevelsTimeframe = source.levels_timeframe || timeframe;
  } else {
    // 1H i 1D: poziomy ZAWSZE z setupu 4H (timeframes.4H.levels w głównym obiekcie instrumentu).
    // Nigdy nie pobieraj poziomów z source.levels bieżącego interwału — 4H jest jedynym źródłem prawdy.
    const levels4h = container.timeframes?.['4H']?.levels || {};
    levels = {
      entry: levels4h.entry != null ? Number(levels4h.entry) : null,
      stop: levels4h.stop != null ? Number(levels4h.stop) : null,
      target: levels4h.target != null ? Number(levels4h.target) : null,
    };
    // Jeśli wszystkie trzy są null (brak poziomów 4H), nie rysuj żadnych poziomów
    const allNull = Object.values(levels).every((v) => v == null);
    if (allNull) {
      levels = {};
    }
    effectiveLevelsTimeframe = '4H';
  }

  const classicAll = ohlc?.classic;
  let classicPatterns = [];
  if (classicAll) {
    const tfData = classicAll.timeframes?.[timeframe] || classicAll.timeframes?.[timeframe === '1D' ? 'Daily' : timeframe];
    const symPatterns = tfData?.symbols?.[symbol] || [];
    classicPatterns = symPatterns.map((p) => ({
      ...p,
      timeframe,
      symbol,
    }));
  }

  return {
    ...source,
    symbol,
    timeframe,
    candles,
    markers,
    harmonics,
    classic_patterns: classicPatterns,
    levels,
    levels_timeframe: effectiveLevelsTimeframe,
    sr_zones: Array.isArray(source.sr_zones) ? source.sr_zones : [],
    sr_zones_timeframe: source.sr_zones_timeframe || timeframe,
    sr_zones_current_price: source.sr_zones_current_price != null ? source.sr_zones_current_price : null,
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
    pattern.points.forEach((point) => {
      const isCompletion = point.label === 'D' || point.label === 'D?' || (pattern.status === 'forming' && point.label === 'C');
      markers.push({
        time: point.time,
        position: bullish ? 'belowBar' : 'aboveBar',
        color: bullish ? '#35d07f' : '#ff4d42',
        shape: 'circle',
        text: isCompletion
          ? `${String(pattern.name || 'H').toUpperCase()} · ${bullish ? 'WZROSTOWA' : 'SPADKOWA'} ${point.label || ''}`
          : point.label || '',
      });
    });
  });
  return markers.sort((a, b) => Number(a.time) - Number(b.time));
}
