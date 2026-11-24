import test from 'node:test';
import assert from 'node:assert/strict';
import { chartMarkers, getChartPayload } from '../src/utils/market.js';

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
  source.harmonics.push({ ...source.harmonics[0], name: 'Bat' });
  const markers = chartMarkers(source);
  assert.equal(markers.length, 7);
  assert.ok(markers.some((marker) => marker.text.startsWith('Butterfly')));
  assert.ok(markers.some((marker) => marker.text.startsWith('Bat')));
});

test('legacy 4H data remains readable but other timeframes are not fabricated', () => {
  const data = { symbols: { eurusd: { candles, markers: [], harmonics: [], levels: {} } } };
  assert.equal(getChartPayload(data, 'eurusd', '4H').candles.length, 3);
  assert.equal(getChartPayload(data, 'eurusd', '1H'), null);
  assert.equal(getChartPayload(data, 'eurusd', '1D'), null);
});
