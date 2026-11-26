import unittest
import pandas as pd
from analysis.decision import make_decision


def frame(hours=30, base=100.0):
    index = pd.date_range("2026-01-01", periods=hours, freq="h", tz="UTC")
    close = pd.Series([base + i * 0.1 for i in range(hours)], index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


class MTFIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.df = frame(30)
        self.renko = {
            "local_low": True, "local_high": False, "last_reversal": True,
            "direction": "up", "prev_leg_length": 3, "last_close": 100.0,
        }
        self.candles = [{"name": "Bullish Engulfing", "direction": "bullish", "strength": "strong"}]

    def test_directional_scores_describe_both_sides(self):
        daily_bullish = {"decision": "LONG", "directional_scores": {"LONG": 80, "SHORT": 0}}
        hourly_bullish = {"decision": "LONG", "directional_scores": {"LONG": 80, "SHORT": 0}}
        result = make_decision(
            self.df, self.renko, [], self.candles,
            daily_analysis=daily_bullish, hourly_analysis=hourly_bullish,
        )
        scores = result["directional_scores"]
        self.assertIn("LONG", scores)
        self.assertIn("SHORT", scores)
        self.assertIsInstance(scores["LONG"], (int, float))
        self.assertIsInstance(scores["SHORT"], (int, float))

    def test_mtf_confirms_long_but_short_gets_conflict(self):
        daily_bullish = {"decision": "LONG", "directional_scores": {"LONG": 80, "SHORT": 0}}
        hourly_bearish = {"decision": "SHORT", "directional_scores": {"LONG": 0, "SHORT": 80}}
        result = make_decision(
            self.df, self.renko, [], self.candles,
            daily_analysis=daily_bullish, hourly_analysis=hourly_bearish,
        )
        # LONG: 1D confirms (+12), 1H conflicts (-8) = +4
        self.assertEqual(result["mtf_long_adjustment"], 80 * 0.15 - 80 * 0.10)
        # SHORT: 1D conflicts (-12), 1H confirms (+8) = -4
        self.assertEqual(result["mtf_short_adjustment"], -80 * 0.15 + 80 * 0.10)

    def test_mtf_neutral_does_not_adjust(self):
        daily_neutral = {"decision": "BRAK", "directional_scores": {"LONG": 0, "SHORT": 0}}
        hourly_neutral = {"decision": "BRAK", "directional_scores": {"LONG": 0, "SHORT": 0}}
        result = make_decision(
            self.df, self.renko, [], self.candles,
            daily_analysis=daily_neutral, hourly_analysis=hourly_neutral,
        )
        self.assertEqual(result["mtf_long_adjustment"], 0.0)
        self.assertEqual(result["mtf_short_adjustment"], 0.0)

    def test_brak_remains_brak_without_pillars_fallback(self):
        weak_candle = [{"name": "Doji", "direction": "neutral", "strength": "weak"}]
        result = make_decision(self.df, {}, [], weak_candle)
        self.assertEqual(result["decision"], "BRAK")

    def test_brak_remains_brak_even_if_one_side_has_higher_conf(self):
        daily_bullish = {"decision": "LONG", "directional_scores": {"LONG": 60, "SHORT": 0}}
        hourly_bearish = {"decision": "SHORT", "directional_scores": {"LONG": 0, "SHORT": 55}}
        result = make_decision(
            self.df, {}, [], [],
            daily_analysis=daily_bullish, hourly_analysis=hourly_bearish,
        )
        self.assertEqual(result["decision"], "BRAK")


if __name__ == "__main__":
    unittest.main()