import unittest
import pandas as pd
from analysis.candles import (
    analyze_candle,
    analyze_candle_sequence,
    candle_analysis_summary,
    _is_candle_closed,
    classify_body,
    classify_wick,
    candle_description,
    BODY_VERY_SMALL_MAX,
    BODY_SMALL_MAX,
    BODY_MEDIUM_MAX,
    WICK_SHORT_MAX,
    WICK_MEDIUM_MAX,
    DOJI_BODY_PCT_MAX,
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


class ClassifyBodyTests(unittest.TestCase):
    def test_body_very_small(self):
        self.assertEqual(classify_body(0.05), "very_small")
        self.assertEqual(classify_body(0.09), "very_small")

    def test_body_small(self):
        self.assertEqual(classify_body(0.10), "small")
        self.assertEqual(classify_body(0.32), "small")

    def test_body_medium(self):
        self.assertEqual(classify_body(0.33), "medium")
        self.assertEqual(classify_body(0.65), "medium")

    def test_body_large(self):
        self.assertEqual(classify_body(0.66), "large")
        self.assertEqual(classify_body(1.0), "large")

    def test_body_none(self):
        self.assertIsNone(classify_body(None))


class ClassifyWickTests(unittest.TestCase):
    def test_wick_short(self):
        self.assertEqual(classify_wick(0.10), "short")
        self.assertEqual(classify_wick(0.14), "short")

    def test_wick_medium(self):
        self.assertEqual(classify_wick(0.15), "medium")
        self.assertEqual(classify_wick(0.39), "medium")

    def test_wick_long(self):
        self.assertEqual(classify_wick(0.40), "long")
        self.assertEqual(classify_wick(0.9), "long")

    def test_wick_none(self):
        self.assertIsNone(classify_wick(None))


class AnalyzeCandleGeometryTests(unittest.TestCase):
    def _df_one(self, o, h, l, c):
        return pd.DataFrame(
            [(o, h, l, c)],
            columns=["open", "high", "low", "close"],
            index=pd.date_range("2026-01-01", periods=1, freq="h", tz="UTC"),
        )

    def test_bullish_candle_full_fields(self):
        df = self._df_one(100.0, 105.0, 99.0, 104.0)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body_direction"], "bullish")
        self.assertEqual(c["body"], 4.0)
        self.assertEqual(c["upper_wick"], 1.0)
        self.assertEqual(c["lower_wick"], 1.0)
        self.assertEqual(c["range"], 6.0)
        self.assertAlmostEqual(c["body_pct"], 4.0 / 6.0, places=4)
        self.assertEqual(c["body_class"], "large")
        self.assertEqual(c["upper_wick_class"], "short")
        self.assertEqual(c["lower_wick_class"], "short")
        self.assertEqual(c["close_location"], "upper")

    def test_bearish_candle_full_fields(self):
        df = self._df_one(104.0, 105.0, 99.0, 100.0)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body_direction"], "bearish")
        self.assertEqual(c["close_location"], "lower")

    def test_neutral_candle(self):
        df = self._df_one(100.0, 101.0, 99.0, 100.0)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body_direction"], "neutral")
        self.assertEqual(c["body"], 0.0)
        self.assertEqual(c["body_class"], "very_small")
        self.assertEqual(c["close_location"], "middle")

    def test_doji_geometry(self):
        df = self._df_one(100.0, 104.0, 96.0, 100.2)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body_direction"], "bullish")
        self.assertAlmostEqual(c["body_pct"], 0.2 / 8.0, places=4)
        self.assertTrue(c["body_pct"] < DOJI_BODY_PCT_MAX)
        self.assertEqual(c["body_class"], "very_small")
        self.assertEqual(c["close_location"], "middle")

    def test_small_body_not_doji(self):
        df = self._df_one(100.0, 101.0, 99.0, 100.6)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["body_direction"], "bullish")
        self.assertAlmostEqual(c["body_pct"], 0.6 / 2.0, places=4)
        self.assertFalse(c["body_pct"] < DOJI_BODY_PCT_MAX)
        self.assertEqual(c["body_class"], "small")

    def test_long_lower_wick(self):
        df = self._df_one(100.0, 100.5, 90.0, 100.4)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["lower_wick_class"], "long")

    def test_long_upper_wick(self):
        df = self._df_one(100.0, 110.0, 99.5, 100.1)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["upper_wick_class"], "long")

    def test_no_wicks(self):
        df = self._df_one(100.0, 100.0, 100.0, 105.0)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["upper_wick"], 0.0)
        self.assertEqual(c["lower_wick"], 0.0)
        self.assertEqual(c["upper_wick_class"], "short")
        self.assertEqual(c["lower_wick_class"], "short")

    def test_zero_range_candle(self):
        df = self._df_one(100.0, 100.0, 100.0, 100.0)
        c = analyze_candle(df, 0, "1H")
        self.assertEqual(c["range"], 0.0)
        self.assertIsNone(c["body_pct"])
        self.assertIsNone(c["body_class"])
        self.assertEqual(c["close_location"], "undefined")

    def test_nan_values_rejected(self):
        df = self._df_one(float("nan"), 101.0, 99.0, 100.0)
        self.assertIsNone(analyze_candle(df, 0, "1H"))


class CandleAnalysisSummaryExtendedTests(unittest.TestCase):
    def _df_multi(self, prices):
        return pd.DataFrame(
            prices,
            columns=["open", "high", "low", "close"],
            index=pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC"),
        )

    def test_summary_has_all_required_fields(self):
        df = self._df_multi([(100.0, 105.0, 99.0, 104.0), (104.0, 106.0, 103.0, 105.0)])
        s = candle_analysis_summary(df, symbol="w20", timeframe="1H")
        lcc = s["last_closed_candle"]
        self.assertIsNotNone(lcc)
        for field in ("is_closed", "symbol", "timeframe", "open", "high", "low", "close",
                      "body", "upper_wick", "lower_wick", "range", "body_direction",
                      "close_location", "close_position", "body_pct", "body_class",
                      "upper_wick_class", "lower_wick_class", "closed_at", "description"):
            self.assertIn(field, lcc)
        self.assertEqual(lcc["symbol"], "w20")
        self.assertEqual(lcc["timeframe"], "1H")
        self.assertTrue(lcc["is_closed"])
        self.assertIsInstance(lcc["description"], str)
        self.assertTrue(lcc["description"].startswith("Świeca"))

    def test_summary_closed_at_is_utc_iso(self):
        df = self._df_multi([(100.0, 105.0, 99.0, 104.0)])
        s = candle_analysis_summary(df, symbol="w20", timeframe="1H")
        lcc = s["last_closed_candle"]
        self.assertIsNotNone(lcc["closed_at"])
        self.assertTrue(lcc["closed_at"].endswith("Z"))

    def test_summary_skips_open_last_candle(self):
        now = pd.Timestamp.now(tz="UTC")
        df = self._df_multi([(100.0, 101.0, 99.0, 100.0)])
        s = candle_analysis_summary(df, symbol="w20", timeframe="1H", now=now)
        self.assertIsNone(s["last_closed_candle"])

    def test_summary_selects_previous_closed_candle(self):
        now = pd.Timestamp.now(tz="UTC")
        df = self._df_multi([(100.0, 101.0, 99.0, 100.0), (101.0, 102.0, 100.0, 101.5)])
        s = candle_analysis_summary(df, symbol="w20", timeframe="1H", now=now)
        lcc = s["last_closed_candle"]
        self.assertIsNotNone(lcc)
        self.assertTrue(lcc["is_closed"])

    def test_summary_1d_timeframe(self):
        df = self._df_multi([(100.0, 105.0, 99.0, 104.0)])
        s = candle_analysis_summary(df, symbol="w20", timeframe="1D")
        lcc = s["last_closed_candle"]
        self.assertIsNotNone(lcc)
        self.assertEqual(lcc["timeframe"], "1D")

    def test_summary_empty_df(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close"])
        s = candle_analysis_summary(df, symbol="w20", timeframe="1H")
        self.assertIsNone(s["last_closed_candle"])
        self.assertEqual(s["last_candle_description"], "Brak danych OHLC")

    def test_summary_none_df(self):
        s = candle_analysis_summary(None, symbol="w20", timeframe="1H")
        self.assertIsNone(s["last_closed_candle"])

    def test_no_lookahead_future_candle_not_selected(self):
        far_future = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=30)
        df = pd.DataFrame(
            [(100.0, 101.0, 99.0, 100.0)],
            columns=["open", "high", "low", "close"],
            index=[far_future],
        )
        s = candle_analysis_summary(df, symbol="w20", timeframe="1H")
        self.assertIsNone(s["last_closed_candle"])


class CandleDescriptionTests(unittest.TestCase):
    def make_candle(self, direction, body_class, upper_wick_class, lower_wick_class,
                    close_location, body_pct=0.5, is_closed=True):
        return {
            "body_direction": direction,
            "body_class": body_class,
            "upper_wick_class": upper_wick_class,
            "lower_wick_class": lower_wick_class,
            "close_location": close_location,
            "body_pct": body_pct,
            "range": 10.0,
            "is_closed": is_closed,
        }

    def test_description_bullish(self):
        c = self.make_candle("bullish", "medium", "short", "long", "upper")
        d = candle_description(c)
        self.assertIn("wzrostowa", d)
        self.assertIn("średni", d)
        self.assertIn("długim", d)

    def test_description_bearish(self):
        c = self.make_candle("bearish", "large", "medium", "short", "lower")
        d = candle_description(c)
        self.assertIn("spadkowa", d)
        self.assertIn("duży", d)

    def test_description_neutral(self):
        c = self.make_candle("neutral", "very_small", "medium", "medium", "middle")
        d = candle_description(c)
        self.assertIn("neutralna", d)

    def test_description_open_candle(self):
        c = self.make_candle("bullish", "medium", "short", "short", "upper", is_closed=False)
        d = candle_description(c)
        self.assertIn("otwarta", d)

    def test_description_none(self):
        self.assertEqual(candle_description(None), "Brak danych świecy")

    def test_all_body_classes(self):
        cases = {
            "very_small": "bardzo małym korpusem",
            "small": "małym korpusem",
            "medium": "średnim korpusem",
            "large": "dużym korpusem",
        }
        for body_class, expected in cases.items():
            c = self.make_candle("neutral", body_class, None, None, "middle", is_closed=True)
            d = candle_description(c)
            self.assertIn(expected, d, f"body_class={body_class} nie daje opisu '{expected}'")

    def test_all_wick_classes(self):
        cases = {
            "short": "krótkim",
            "medium": "średnim",
            "long": "długim",
        }
        for wick_class, expected in cases.items():
            c = self.make_candle("neutral", "medium", wick_class, None, "middle", is_closed=True)
            d = candle_description(c)
            self.assertIn(expected, d, f"upper_wick_class={wick_class} nie daje opisu '{expected}'")

    def test_doji_description(self):
        c = self.make_candle("bullish", "very_small", "short", "short", "middle", body_pct=0.02, is_closed=True)
        d = candle_description(c)
        self.assertIn("(Doji)", d)

    def test_no_english_class_names_in_description(self):
        c = self.make_candle("bullish", "large", "long", "short", "upper", is_closed=True)
        d = candle_description(c)
        for english in ("very_small", "small", "medium", "large", "short", "long"):
            self.assertNotIn(english, d, f"Angielska nazwa klasy '{english}' występuje w opisie: {d}")


if __name__ == "__main__":
    unittest.main()