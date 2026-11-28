import test from 'node:test';
import assert from 'node:assert/strict';
import { chartMarkers, currentDecision, formatPrice, getChartPayload } from '../src/utils/market.js';

const candles = [
  { time: 100, open: 1, high: 1.2, low: 0.9, close: 1.1 },
  { time: 200, open: 1.1, high: 1.3, low: 1, close: 1.2 },
  { time: 300, open: 1.2, high: 1.4, low: 1.1, close: 1.3 },
];

function payload(symbol = 'eurusd', timeframe = '4H') {
  return {
    symbol, timeframe, candles,
    markers: [{ time: 100, symbol, timeframe, text: 'Hammer' }],
    harmonics: [{
      name: 'Butterfly', symbol, timeframe, direction: 'bullish', status: 'completed',
      points: [
        { time: 100, value: 1, label: 'X' }, { time: 200, value: 1.3, label: 'A' },
        { time: 300, value: 1.1, label: 'B' },
      ],
    }],
    levels: { entry: 1.2, stop: 1, target: 1.5 }, levels_timeframe: timeframe,
  };
}

test('selects the requested timeframe instead of substituting 4H', () => {
  const hourly = { ...payload('eurusd', '1H'), candles: candles.map((c) => ({ ...c, close: 1.15 })) };
  const data = { symbols: { eurusd: { timeframes: { '4H': payload(), '1H': hourly } } } };
  const result = getChartPayload(data, 'eurusd', '1H');
  assert.equal(result.timeframe, '1H');
  assert.equal(result.candles[0].close, 1.15);
});

test('rejects a chart whose source belongs to another instrument', () => {
  const data = { symbols: { eurusd: { timeframes: { '4H': payload('gold', '4H') } } } };
  assert.equal(getChartPayload(data, 'eurusd', '4H'), null);
});

test('filters foreign and out-of-range overlays', () => {
  const source = payload();
  source.harmonics.push(
    { ...source.harmonics[0], symbol: 'gold' },
    { ...source.harmonics[0], timeframe: '1H' },
    { ...source.harmonics[0], points: [{ time: 999, value: 4000, label: 'X' }] },
  );
  source.markers.push({ time: 100, symbol: 'gold', timeframe: '4H' });
  const result = getChartPayload({ symbols: { eurusd: source } }, 'eurusd', '4H');
  assert.equal(result.harmonics.length, 1);
  assert.equal(result.markers.length, 1);
  assert.ok(result.candles.every((candle) => candle.high < 2));
});

test('keeps markers from all formations instead of overwriting them', () => {
  const source = payload();
  source.harmonics[0].points.push({ time: 300, value: 1.2, label: 'D' });
  source.harmonics.push({ ...source.harmonics[0], name: 'Bat' });
  const markers = chartMarkers(source);
  assert.equal(markers.length, 9);
  assert.ok(markers.some((marker) => marker.text.startsWith('BUTTERFLY')));
  assert.ok(markers.some((marker) => marker.text.startsWith('BAT')));
});

test('legacy 4H data remains readable but other timeframes are not fabricated', () => {
  const data = { symbols: { eurusd: { candles, markers: [], harmonics: [], levels: {} } } };
  assert.equal(getChartPayload(data, 'eurusd', '4H').candles.length, 3);
  assert.equal(getChartPayload(data, 'eurusd', '1H'), null);
  assert.equal(getChartPayload(data, 'eurusd', '1D'), null);
});
test('terminal and legacy historical signals are not presented as opportunities', () => {
  assert.equal(currentDecision({ decision: 'LONG', signal_status: 'TAKE_PROFIT' }), 'BRAK');
  assert.equal(currentDecision({ decision: 'LONG', harmonic: { lifecycle: 'historical' } }), 'BRAK');
  assert.equal(currentDecision({ decision: 'SHORT', signal_status: 'PENDING', can_enter: true }), 'SHORT');
});

test('price formatting rounds only presentation values', () => {
  assert.equal(formatPrice(3555.3999), '3555');
  assert.equal(formatPrice(3502.29987), '3502');
  assert.equal(formatPrice(null), '—');
});

test('terminal chart signals do not retain transaction levels', () => {
  const source = { ...payload(), signal_status: 'STOP_LOSS' };
  const result = getChartPayload({ symbols: { eurusd: source } }, 'eurusd', '4H');
  assert.deepEqual(result.levels, {});
});

test('harmonics source: panel receives same geometry as chart from ohlc.json', () => {
  const usdpln4h = {
    symbol: 'usdpln', timeframe: '4H',
    candles: [
      { time: 100, open: 1, high: 1.2, low: 0.9, close: 1.1 },
      { time: 200, open: 1.1, high: 1.3, low: 1, close: 1.2 },
      { time: 250, open: 1.2, high: 1.4, low: 1.1, close: 1.3 },
      { time: 300, open: 1.3, high: 1.5, low: 1.2, close: 1.4 },
      { time: 350, open: 1.4, high: 1.6, low: 1.3, close: 1.5 },
    ],
    harmonics: [{
      name: 'Butterfly', symbol: 'usdpln', timeframe: '4H', direction: 'bullish',
      lifecycle: 'forming', status: 'forming',
      points: [
        { time: 100, value: 4.0573, label: 'X' },
        { time: 200, value: 4.1020, label: 'A' },
        { time: 250, value: 4.0655, label: 'B' },
        { time: 300, value: 4.0891, label: 'C' },
        { time: 350, value: 4.0374, label: 'D?' },
      ],
    }],
    levels: { entry: null, stop: null, target: null }, levels_timeframe: '4H',
  };
  const data = { symbols: { usdpln: { timeframes: { '4H': usdpln4h } } } };
  const result = getChartPayload(data, 'usdpln', '4H');
  assert.equal(result.harmonics.length, 1);
  assert.equal(result.harmonics[0].name, 'Butterfly');
  assert.equal(result.harmonics[0].timeframe, '4H');
  assert.equal(result.harmonics[0].points.length, 5);
  assert.deepEqual(result.harmonics[0].points.map(p => p.label), ['X', 'A', 'B', 'C', 'D?']);
});

test('harmony with empty points is not rendered as complete geometry', () => {
  const source = {
    symbol: 'eurusd', timeframe: '4H', candles,
    harmonics: [{
      name: 'Bat', symbol: 'eurusd', timeframe: '4H', direction: 'bearish',
      lifecycle: 'forming', status: 'forming',
      points: [],
    }],
    levels: { entry: null, stop: null, target: null }, levels_timeframe: '4H',
  };
  const data = { symbols: { eurusd: { timeframes: { '4H': source } } } };
  const result = getChartPayload(data, 'eurusd', '4H');
  assert.equal(result.harmonics.length, 0);
});

test('harmonics with lifecycle outside forming/active is not shown', () => {
  const source = {
    symbol: 'eurusd', timeframe: '4H', candles,
    harmonics: [
      { ...payload().harmonics[0], lifecycle: 'completed', status: 'completed' },
      { ...payload().harmonics[0], lifecycle: 'expired', status: 'expired' },
      { ...payload().harmonics[0], lifecycle: 'forming', status: 'forming' },
    ],
    levels: { entry: null, stop: null, target: null }, levels_timeframe: '4H',
  };
  const data = { symbols: { eurusd: { timeframes: { '4H': source } } } };
  const result = getChartPayload(data, 'eurusd', '4H');
  assert.equal(result.harmonics.length, 1);
  assert.equal(result.harmonics[0].lifecycle, 'forming');
});

test('missing harmonics does not cause rendering error', () => {
  const source = {
    symbol: 'eurusd', timeframe: '4H', candles,
    harmonics: [],
    levels: { entry: null, stop: null, target: null }, levels_timeframe: '4H',
  };
  const data = { symbols: { eurusd: { timeframes: { '4H': source } } } };
  const result = getChartPayload(data, 'eurusd', '4H');
  assert.equal(result.harmonics.length, 0);
  assert.ok(Array.isArray(result.harmonics));
});

function extractLastClosedCandle(instrument, timeframe = '4H') {
  if (!instrument) return null;
  const tfKey = timeframe === '1D' ? '1D' : timeframe;
  const tfData = instrument?.timeframes?.[tfKey]
    || (timeframe === '1D' ? instrument?.timeframes?.Daily : null)
    || {};
  return tfData.last_closed_candle || null;
}

test('extracts last_closed_candle from instrument timeframes', () => {
  const lcc = {
    is_closed: true, symbol: 'w20', timeframe: '4H',
    open: 4000, high: 4050, low: 3950, close: 4030,
    body: 30, upper_wick: 20, lower_wick: 10, range: 100,
    body_pct: 0.3, body_direction: 'bullish', body_class: 'medium',
    upper_wick_class: 'short', lower_wick_class: 'short',
    close_location: 'upper', close_position: 0.8,
    closed_at: '2026-11-26T16:00:00Z',
    description: 'Świeca wzrostowa z średnim korpusem.',
  };
  const instrument = {
    symbol: 'w20',
    timeframes: { '4H': { last_closed_candle: lcc } },
  };
  assert.deepEqual(extractLastClosedCandle(instrument, '4H'), lcc);
});

test('returns null when instrument is null', () => {
  assert.equal(extractLastClosedCandle(null, '4H'), null);
});

test('returns null when last_closed_candle is missing', () => {
  const instrument = { symbol: 'w20', timeframes: { '4H': {} } };
  assert.equal(extractLastClosedCandle(instrument, '4H'), null);
});

test('returns null when timeframe data is missing', () => {
  const instrument = { symbol: 'w20', timeframes: {} };
  assert.equal(extractLastClosedCandle(instrument, '4H'), null);
});

test('handles null and invalid numeric values in candle', () => {
  const lcc = {
    is_closed: true, symbol: 'w20', timeframe: '4H',
    open: null, high: NaN, low: undefined, close: 'invalid',
    body: null, upper_wick: null, lower_wick: null, range: null,
    body_pct: null, body_direction: 'unknown', body_class: null,
    upper_wick_class: null, lower_wick_class: null,
    close_location: null, close_position: null,
    closed_at: null, description: null,
  };
  const instrument = { symbol: 'w20', timeframes: { '4H': { last_closed_candle: lcc } } };
  const extracted = extractLastClosedCandle(instrument, '4H');
  assert.equal(extracted.is_closed, true);
  assert.equal(extracted.open, null);
  assert.equal(extracted.body_direction, 'unknown');
});

test('supports 1H, 4H and 1D timeframe keys', () => {
  const lcc4h = { is_closed: true, timeframe: '4H', close: 100 };
  const lcc1h = { is_closed: true, timeframe: '1H', close: 101 };
  const lcc1d = { is_closed: true, timeframe: '1D', close: 102 };
  const instrument = {
    symbol: 'w20',
    timeframes: {
      '4H': { last_closed_candle: lcc4h },
      '1H': { last_closed_candle: lcc1h },
      Daily: { last_closed_candle: lcc1d },
    },
  };
  assert.equal(extractLastClosedCandle(instrument, '4H'), lcc4h);
  assert.equal(extractLastClosedCandle(instrument, '1H'), lcc1h);
  assert.equal(extractLastClosedCandle(instrument, '1D'), lcc1d);
});
