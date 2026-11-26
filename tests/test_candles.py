import unittest
import pandas as pd
from analysis.candles import (
    analyze_candle,
    analyze_candle_sequence,
    candle_analysis_summary,
    _is_candle_closed,
)


def make_df(prices):
    index = pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC")
    return pd.DataFrame(prices, columns=["open", "high", "low", "close"], index=index)


class AnalyzeCandleTests(unittest.TestCase):
    def test_bullish_candle_fields(self):
        df = make_df([(100.0, 102.0, 99.0, 101.0)])
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body"], 1.0)
        self.assertEqual(c["upper_wick"], 1.0)
        self.assertEqual(c["lower_wick"], 1.0)
        self.assertEqual(c["range"], 3.0)
        self.assertEqual(c["body_direction"], "bullish")
        self.assertEqual(c["close_location"], "upper")
        self.assertIsNotNone(c["close_position"])
        self.assertGreater(c["close_position"], 0.5)

    def test_bearish_candle_fields(self):
        df = make_df([(101.0, 102.0, 99.0, 99.5)])
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body_direction"], "bearish")
        self.assertEqual(c["close_location"], "lower")
        self.assertLess(c["close_position"], 0.33)

    def test_doji_candle(self):
        df = make_df([(100.0, 101.0, 99.0, 100.0)])
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body"], 0.0)
        self.assertEqual(c["body_direction"], "neutral")
        self.assertEqual(c["close_location"], "middle")

    def test_zero_range_candle(self):
        df = make_df([(100.0, 100.0, 100.0, 100.0)])
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["range"], 0.0)
        self.assertEqual(c["close_location"], "undefined")
        self.assertIsNone(c["close_position"])

    def test_empty_df_returns_none(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close"])
        self.assertIsNone(analyze_candle(df, 0, "1H"))

    def test_none_df_returns_none(self):
        self.assertIsNone(analyze_candle(None, 0, "1H"))

    def test_nan_values_rejected(self):
        df = make_df([(float("nan"), 101.0, 99.0, 100.0)])
        self.assertIsNone(analyze_candle(df, 0, "1H"))

    def test_is_closed_for_past_candle(self):
        # Świeca z 2026-01-01 00:00 UTC na 1H kończy się o 01:00, teraz jest 2026-11-26
        df = make_df([(100.0, 101.0, 99.0, 100.0)])
        self.assertTrue(_is_candle_closed("2026-01-01 00:00:00+00:00", "1H"))

    def test_is_open_for_future_candle(self):
        far_future = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=30)
        self.assertFalse(_is_candle_closed(str(far_future), "1H"))

    def test_last_candle_default_index(self):
        df = make_df([(100.0, 101.0, 99.0, 100.0), (101.0, 102.0, 100.0, 101.5)])
        c = analyze_candle(df, -1, "1H")
        self.assertEqual(c["close"], 101.5)


class AnalyzeCandleSequenceTests(unittest.TestCase):
    def test_sequence_description_and_count(self):
        df = make_df([
            (100.0, 101.0, 99.0, 101.0),  # bullish
            (101.0, 102.0, 100.0, 100.5),  # bearish
            (100.5, 102.0, 100.0, 101.5),  # bullish
        ])
        seq = analyze_candle_sequence(df, lookback=5, timeframe="1H")
        self.assertEqual(len(seq["candles"]), 3)
        self.assertIn("wzrostowa", seq["description"])
        self.assertIn("spadkowa", seq["description"])
        self.assertEqual(seq["timeframe"], "1H")
        self.assertIsNotNone(seq["analyzed_at"])

    def test_empty_df_sequence(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close"])
        seq = analyze_candle_sequence(df, lookback=5, timeframe="1H")
        self.assertEqual(seq["candles"], [])
        self.assertEqual(seq["description"], "Brak danych OHLC")

    def test_none_df_sequence(self):
        seq = analyze_candle_sequence(None, lookback=5, timeframe="1H")
        self.assertEqual(seq["candles"], [])


class CandleAnalysisSummaryTests(unittest.TestCase):
    def test_summary_structure(self):
        df = make_df([
            (100.0, 101.0, 99.0, 101.0),
            (101.0, 102.0, 100.0, 100.5),
        ])
        s = candle_analysis_summary(df, timeframe="1H", lookback=3)
        self.assertEqual(s["timeframe"], "1H")
        self.assertIsNotNone(s["analyzed_at"])
        self.assertIsInstance(s["last_candle_description"], str)
        self.assertIsInstance(s["sequence_description"], str)
        self.assertIsInstance(s["candles"], list)

    def test_summary_last_closed_candle(self):
        df = make_df([
            (100.0, 101.0, 99.0, 101.0),  # zamknięta (przeszłość)
        ])
        s = candle_analysis_summary(df, timeframe="1H")
        self.assertIsNotNone(s["last_closed_candle"])
        self.assertTrue(s["last_closed_candle"]["is_closed"])
        self.assertIn("Ostatnia zamknięta świeca", s["last_candle_description"])

    def test_empty_df_summary(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close"])
        s = candle_analysis_summary(df, timeframe="1H")
        self.assertEqual(s["last_candle_description"], "Brak danych OHLC")
        self.assertEqual(s["sequence_description"], "Brak danych OHLC")
        self.assertIsNone(s["last_closed_candle"])


if __name__ == "__main__":
    unittest.main()