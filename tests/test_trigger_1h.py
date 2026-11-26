import unittest
import pandas as pd
from analysis.analyzer import evaluate_trigger_1h


def make_1h_df(rows):
    index = pd.date_range("2026-01-01", periods=len(rows), freq="h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)


class Trigger1HTests(unittest.TestCase):
    def test_long_close_above_resistance(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (104, 106, 104, 106),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, level = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertTrue(confirmed)
        self.assertEqual(level, 105.0)

    def test_short_close_below_support(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (94, 96, 93, 93),
        ])
        zones = [{"type": "SUPPORT", "lower": 94.0, "upper": 95.0, "center": 94.5}]
        confirmed, level = evaluate_trigger_1h(df, zones, 1.0, "SHORT")
        self.assertTrue(confirmed)
        self.assertEqual(level, 94.0)

    def test_long_close_without_breakout(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (104, 105, 104, 104.5),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_short_close_without_breakout(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (95, 96, 94.5, 95.5),
        ])
        zones = [{"type": "SUPPORT", "lower": 95.0, "upper": 96.0, "center": 95.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "SHORT")
        self.assertFalse(confirmed)

    def test_wick_breakout_but_close_not_trigger(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (104, 107, 104, 104.5),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_unclosed_candle_no_trigger(self):
        index = pd.date_range("2030-01-01", periods=2, freq="h", tz="UTC")
        df = pd.DataFrame(
            [(100, 101, 99, 100), (104, 106, 104, 105.5)],
            columns=["open", "high", "low", "close"],
            index=index,
        )
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_bullish_formation_inside_support_zone(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (99, 99.8, 97, 99.6),
        ])
        zones = [{"type": "SUPPORT", "lower": 98.0, "upper": 100.0, "center": 99.0}]
        confirmed, level = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertTrue(confirmed)
        self.assertEqual(level, 99.0)

    def test_bullish_formation_05_atr_from_support(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 100.8, 97, 100.6),
        ])
        zones = [{"type": "SUPPORT", "lower": 99.0, "upper": 100.0, "center": 99.5}]
        confirmed, level = evaluate_trigger_1h(df, zones, 3.0, "LONG")
        self.assertTrue(confirmed)
        self.assertEqual(level, 99.5)

    def test_formation_outside_zone_no_trigger(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (110, 111, 109, 110.5),
        ])
        zones = [{"type": "SUPPORT", "lower": 98.0, "upper": 100.0, "center": 99.0}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_opposite_formation_no_trigger(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (99, 100, 98, 98.5),
        ])
        zones = [{"type": "SUPPORT", "lower": 98.0, "upper": 100.0, "center": 99.0}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_no_sr_zone_no_trigger(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (106, 107, 105, 106),
        ])
        confirmed, _ = evaluate_trigger_1h(df, [], 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_long_and_short_independent(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (106, 107, 105, 106),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        conf_long, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        conf_short, _ = evaluate_trigger_1h(df, zones, 1.0, "SHORT")
        self.assertTrue(conf_long)
        self.assertFalse(conf_short)

    def test_no_lookahead_only_last_closed(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (104, 104.5, 104, 104.2),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_pending_status_not_used(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (104, 104.5, 104, 104.2),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "LONG")
        self.assertFalse(confirmed)

    def test_active_status_not_used(self):
        df = make_1h_df([
            (100, 101, 99, 100),
            (104, 104.5, 104, 104.2),
        ])
        zones = [{"type": "RESISTANCE", "lower": 104.0, "upper": 105.0, "center": 104.5}]
        confirmed, _ = evaluate_trigger_1h(df, zones, 1.0, "SHORT")
        self.assertFalse(confirmed)


if __name__ == "__main__":
    unittest.main()