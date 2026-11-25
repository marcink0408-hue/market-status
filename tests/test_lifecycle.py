import unittest

import pandas as pd

from analysis.decision import make_decision
from analysis.lifecycle import evaluate_harmonic, evaluate_signal, harmonic_is_visible


def frame(rows):
    index = pd.date_range("2026-01-01", periods=len(rows), freq="4h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)


def harmonic():
    return {
        "name": "Butterfly", "direction": "bullish", "status": "completed",
        "X": 105.0, "A": 110.0, "B": 106.0, "C": 108.0, "D": 100.0,
        "time_X": "2026-01-01 00:00:00+00:00",
        "time_A": "2026-01-01 04:00:00+00:00",
        "time_B": "2026-01-01 08:00:00+00:00",
        "time_C": "2026-01-01 12:00:00+00:00",
        "time_D": "2026-01-01 16:00:00+00:00",
    }


class HarmonicLifecycleTests(unittest.TestCase):
    def test_price_below_d_invalidates_bullish_butterfly(self):
        df = frame([(105, 106, 104, 105)] * 4 + [(101, 102, 100, 101),
                   (101, 102, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100)])
        result = evaluate_harmonic(harmonic(), df, "4H")
        self.assertEqual(result["lifecycle"], "invalidated")
        self.assertFalse(result["active"])
        self.assertEqual(result["close_reason"], "price_beyond_D")

    def test_standard_pattern_target_closes_formation(self):
        df = frame([(105, 106, 104, 105)] * 4 + [(101, 102, 100, 101),
                   (101, 105, 100, 104), (104, 105, 103, 104), (104, 105, 103, 104)])
        result = evaluate_harmonic(harmonic(), df, "4H")
        self.assertEqual(result["lifecycle"], "target_reached")
        self.assertAlmostEqual(result["pattern_target"], 103.82)

    def test_old_closed_pattern_is_not_visible_after_five_days(self):
        pattern = dict(harmonic(), lifecycle="invalidated", closed_at="2026-01-01T20:00:00Z")
        df = frame([(100, 101, 99, 100)] * 40)
        self.assertFalse(harmonic_is_visible(pattern, df))


class SignalLifecycleTests(unittest.TestCase):
    def decision(self, **levels):
        return dict({
            "decision": "LONG", "entry": 110.123456, "stop": 95.123456,
            "target": 120.123456, "last_bar_time": "2026-01-01 00:00:00+00:00",
            "harmonic": None,
        }, **levels)

    def test_pending_signal_preserves_full_level_precision(self):
        df = frame([(100, 101, 99, 100), (100, 102, 99, 101)])
        result = evaluate_signal(self.decision(), df, "4H")
        self.assertEqual(result["signal_status"], "PENDING")
        self.assertTrue(result["can_enter"])
        self.assertEqual(result["entry"], 110.123456)
        self.assertEqual(result["signal_valid_until"], "2026-01-01T04:00:00Z")

    def test_entry_then_take_profit_is_not_a_new_opportunity(self):
        df = frame([(100, 111, 99, 110), (110, 121, 109, 120)])
        result = evaluate_signal(self.decision(), df, "4H")
        self.assertEqual(result["signal_status"], "TAKE_PROFIT")
        self.assertFalse(result["can_enter"])

    def test_entry_then_stop_loss_is_terminal(self):
        df = frame([(100, 111, 99, 110), (110, 112, 94, 96)])
        result = evaluate_signal(self.decision(), df, "4H")
        self.assertEqual(result["signal_status"], "STOP_LOSS")
        self.assertFalse(result["can_enter"])

    def test_invalidated_harmonic_cannot_confirm_new_decision(self):
        df = frame([(100 + i, 102 + i, 99 + i, 101 + i) for i in range(20)])
        pattern = dict(harmonic(), lifecycle="invalidated", active=False)
        candles = [{"name": "Bullish Engulfing", "direction": "bullish", "strength": "strong"}]
        result = make_decision(df, {}, [pattern], candles)
        self.assertEqual(result["decision"], "BRAK")

    def test_forming_pattern_has_fixed_structure_based_expiry(self):
        df = frame([(100, 101, 99, 100)] * 10)
        pattern = {
            "status": "forming", "time_B": "2026-01-01 12:00:00+00:00",
            "time_C": "2026-01-01 16:00:00+00:00",
        }
        result = evaluate_harmonic(pattern, df, "4H")
        self.assertEqual(result["valid_until"], "2026-01-01T20:00:00Z")
        self.assertEqual(result["lifecycle"], "expired")

    def test_untouched_entry_expires_after_signal_candle(self):
        df = frame([(100, 101, 99, 100)] * 3)
        result = evaluate_signal(self.decision(), df, "4H")
        self.assertEqual(result["signal_status"], "EXPIRED")
        self.assertFalse(result["can_enter"])


if __name__ == "__main__":
    unittest.main()
