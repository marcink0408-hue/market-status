import unittest
import pandas as pd
import numpy as np
import os
import json
import tempfile
from unittest.mock import patch

from analysis.classic_patterns import (
    detect_for_symbol_tf,
    update_patterns_for_symbol_tf,
    _atr, _pivots, _pattern_id,
    _detect_double_top_bottom, _detect_triangle, _detect_wedge,
    _detect_flag_pennant, _detect_head_and_shoulders, _detect_channel,
    _check_breakout, _check_retest, _status_can_transition,
    STATUS_FORMING, STATUS_CONFIRMED, STATUS_BREAKOUT, STATUS_RETEST,
    STATUS_INVALIDATED, STATUS_EXPIRED,
    CLASSIC_MAX_PATTERNS_PER_TF,
)
from config import CLASSIC_PATTERN_TIMEFRAMES


def make_df(prices):
    index = pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC")
    return pd.DataFrame(prices, columns=["open", "high", "low", "close"], index=index)


class AtrTests(unittest.TestCase):
    def test_atr_positive(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(20)])
        atr = _atr(df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy())
        self.assertTrue(np.all(atr[14:] > 0))

    def test_atr_nan_for_insufficient(self):
        df = make_df([(100, 101, 99, 100)] * 5)
        atr = _atr(df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy())
        self.assertTrue(np.all(np.isnan(atr)))


class PivotTests(unittest.TestCase):
    def test_pivots_require_confirmation_bars(self):
        prices = [(100 + i, 105 + i, 99 + i, 100 + i) for i in range(20)]
        df = make_df(prices)
        highs, lows = _pivots(df["high"].to_numpy(), df["low"].to_numpy(), confirm=3)
        last_idx = len(df) - 1
        for _, _ in highs + lows:
            self.assertLessEqual(_, last_idx - 3)

    def test_pivots_detect_high_and_low(self):
        prices = [
            (100, 101, 99, 100), (100, 102, 99, 101), (100, 103, 99, 102),
            (100, 104, 99, 103), (100, 110, 99, 105),
            (100, 106, 99, 104), (100, 105, 99, 103), (100, 104, 99, 102),
            (100, 103, 99, 101), (100, 102, 99, 100),
        ]
        df = make_df(prices)
        highs, lows = _pivots(df["high"].to_numpy(), df["low"].to_numpy(), confirm=3)
        self.assertTrue(any(p == 110.0 for _, p in highs))


class PatternIdTests(unittest.TestCase):
    def test_deterministic_id(self):
        id1 = _pattern_id("w20", "4H", "double_top", [(1, 100.0), (5, 100.0)])
        id2 = _pattern_id("w20", "4H", "double_top", [(1, 100.0), (5, 100.0)])
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 24)

    def test_different_symbols_different_id(self):
        id1 = _pattern_id("w20", "4H", "double_top", [(1, 100.0)])
        id2 = _pattern_id("us500", "4H", "double_top", [(1, 100.0)])
        self.assertNotEqual(id1, id2)

    def test_different_timeframes_different_id(self):
        id1 = _pattern_id("w20", "4H", "double_top", [(1, 100.0)])
        id2 = _pattern_id("w20", "1H", "double_top", [(1, 100.0)])
        self.assertNotEqual(id1, id2)


class DoubleTopBottomTests(unittest.TestCase):
    def test_double_top_detected(self):
        highs = [(0, 100.0), (10, 100.5)]
        lows = [(5, 95.0)]
        high_arr = np.array([100.0] * 15)
        low_arr = np.array([95.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_double_top_bottom(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        self.assertTrue(any(r["type"] == "double_top" for r in result))

    def test_double_bottom_detected(self):
        highs = [(5, 105.0)]
        lows = [(0, 100.0), (10, 100.5)]
        high_arr = np.array([100.0] * 15)
        low_arr = np.array([100.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_double_top_bottom(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        self.assertTrue(any(r["type"] == "double_bottom" for r in result))

    def test_double_top_neckline(self):
        highs = [(0, 100.0), (10, 100.0)]
        lows = [(5, 95.0)]
        high_arr = np.array([100.0] * 15)
        low_arr = np.array([95.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_double_top_bottom(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        tops = [r for r in result if r["type"] == "double_top"]
        self.assertTrue(len(tops) > 0)
        self.assertIn("neckline", str(tops[0]["trendlines"]))


class TriangleTests(unittest.TestCase):
    def test_symmetrical_triangle_detected(self):
        highs = [(0, 110.0), (5, 108.0)]
        lows = [(0, 100.0), (5, 102.0)]
        high_arr = np.array([110.0] * 15)
        low_arr = np.array([100.0] * 15)
        close_arr = np.array([105.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_triangle(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        triangles = [r for r in result if r["type"] == "triangle"]
        self.assertTrue(len(triangles) > 0)
        self.assertEqual(triangles[0]["subtype"], "symmetrical")

    def test_ascending_triangle_detected(self):
        highs = [(0, 110.0), (5, 110.0)]
        lows = [(0, 100.0), (5, 102.0)]
        high_arr = np.array([110.0] * 15)
        low_arr = np.array([100.0] * 15)
        close_arr = np.array([105.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_triangle(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        triangles = [r for r in result if r["type"] == "triangle"]
        ascending = [t for t in triangles if t["subtype"] == "ascending"]
        self.assertTrue(len(ascending) > 0)

    def test_triangle_has_apex(self):
        highs = [(0, 110.0), (5, 108.0)]
        lows = [(0, 100.0), (5, 102.0)]
        high_arr = np.array([110.0] * 15)
        low_arr = np.array([100.0] * 15)
        close_arr = np.array([105.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_triangle(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        self.assertTrue(any("apex" in r for r in result))


class WedgeTests(unittest.TestCase):
    def test_rising_wedge_detected(self):
        highs = [(0, 100.0), (5, 102.0)]
        lows = [(0, 98.0), (5, 100.0)]
        high_arr = np.array([100.0] * 15)
        low_arr = np.array([98.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_wedge(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        wedges = [r for r in result if r["type"] == "wedge"]
        rising = [w for w in wedges if w["subtype"] == "rising"]
        self.assertTrue(len(rising) > 0)

    def test_falling_wedge_detected(self):
        highs = [(0, 102.0), (5, 100.0)]
        lows = [(0, 100.0), (5, 98.0)]
        high_arr = np.array([102.0] * 15)
        low_arr = np.array([100.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_wedge(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        wedges = [r for r in result if r["type"] == "wedge"]
        falling = [w for w in wedges if w["subtype"] == "falling"]
        self.assertTrue(len(falling) > 0)


class FlagPennantTests(unittest.TestCase):
    def test_bullish_flag_detected(self):
        high_arr = np.array([100.0 + i for i in range(25)])
        low_arr = np.array([98.0 + i for i in range(25)])
        close_arr = np.array([99.0 + i for i in range(25)])
        atr_arr = np.array([1.0] * 25)
        highs = []
        lows = []
        for i in range(15, 25):
            highs.append((i, 24.0 + i))
            lows.append((i, 22.0 + i))
        result = _detect_flag_pennant(
            high_arr, low_arr, close_arr, atr_arr, highs, lows, 24, 0.5,
            impulse_mult=2.0, min_cons=4, max_cons=20,
        )
        self.assertTrue(len(result) > 0)


class HeadAndShouldersTests(unittest.TestCase):
    def test_head_and_shoulders_detected(self):
        highs = [(0, 100.0), (5, 110.0), (10, 100.0)]
        lows = [(2, 95.0), (7, 95.0)]
        high_arr = np.array([100.0] * 15)
        low_arr = np.array([95.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_head_and_shoulders(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        hns = [r for r in result if r["type"] == "head_and_shoulders"]
        self.assertTrue(len(hns) > 0)
        self.assertEqual(hns[0]["direction"], "bearish")

    def test_inverse_head_and_shoulders_detected(self):
        lows = [(0, 100.0), (5, 90.0), (10, 100.0)]
        highs = [(2, 105.0), (7, 105.0)]
        high_arr = np.array([105.0] * 15)
        low_arr = np.array([100.0] * 15)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_head_and_shoulders(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5)
        ihs = [r for r in result if r["type"] == "inverse_head_and_shoulders"]
        self.assertTrue(len(ihs) > 0)
        self.assertEqual(ihs[0]["direction"], "bullish")


class ChannelTests(unittest.TestCase):
    def test_ascending_channel_detected(self):
        highs = [(0, 100.0), (5, 105.0)]
        lows = [(0, 95.0), (5, 100.0)]
        high_arr = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0] + [105.0] * 9)
        low_arr = np.array([95.0, 96.0, 97.0, 98.0, 99.0, 100.0] + [100.0] * 9)
        close_arr = np.array([100.0] * 15)
        atr_arr = np.array([1.0] * 15)
        result = _detect_channel(high_arr, low_arr, close_arr, atr_arr, highs, lows, 14, 0.5, 0.3)
        channels = [r for r in result if r["type"] == "channel"]
        self.assertTrue(len(channels) > 0)


class BreakoutRetestTests(unittest.TestCase):
    def test_breakout_requires_close_beyond_boundary(self):
        pattern = {"boundary": {"upper": 100.0, "lower": 90.0}, "direction": "bullish"}
        is_bo, _ = _check_breakout(100.0, 101.0, 99.0, pattern, "bullish", 1.0)
        self.assertFalse(is_bo)
        is_bo, _ = _check_breakout(100.5, 101.0, 99.0, pattern, "bullish", 1.0)
        self.assertTrue(is_bo)

    def test_breakout_bearish(self):
        pattern = {"boundary": {"upper": 100.0, "lower": 90.0}, "direction": "bearish"}
        is_bo, _ = _check_breakout(89.5, 91.0, 89.0, pattern, "bearish", 1.0)
        self.assertTrue(is_bo)

    def test_retest_within_buffer(self):
        self.assertTrue(_check_retest(100.0, 100.0, 1.0))
        self.assertTrue(_check_retest(100.7, 100.0, 1.0))
        self.assertFalse(_check_retest(102.0, 100.0, 1.0))


class StatusTransitionTests(unittest.TestCase):
    def test_status_cannot_regress(self):
        self.assertTrue(_status_can_transition(STATUS_FORMING, STATUS_CONFIRMED))
        self.assertTrue(_status_can_transition(STATUS_CONFIRMED, STATUS_BREAKOUT))
        self.assertTrue(_status_can_transition(STATUS_BREAKOUT, STATUS_RETEST))
        self.assertFalse(_status_can_transition(STATUS_BREAKOUT, STATUS_CONFIRMED))
        self.assertFalse(_status_can_transition(STATUS_INVALIDATED, STATUS_FORMING))

    def test_status_order(self):
        self.assertEqual(STATUS_FORMING, "FORMUJĄCA SIĘ")
        self.assertEqual(STATUS_CONFIRMED, "POTWIERDZONA")
        self.assertEqual(STATUS_BREAKOUT, "WYBITA")
        self.assertEqual(STATUS_RETEST, "RETEST")
        self.assertEqual(STATUS_INVALIDATED, "UNIEWAŻNIONA")
        self.assertEqual(STATUS_EXPIRED, "WYGASŁA")


class DetectionTests(unittest.TestCase):
    def test_detect_returns_list(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        result = detect_for_symbol_tf(df, "test", "4H")
        self.assertIsInstance(result, list)

    def test_insufficient_data_returns_empty(self):
        df = make_df([(100, 101, 99, 100)] * 10)
        result = detect_for_symbol_tf(df, "test", "4H")
        self.assertEqual(result, [])

    def test_timeframes_supported(self):
        self.assertIn("1H", CLASSIC_PATTERN_TIMEFRAMES)
        self.assertIn("4H", CLASSIC_PATTERN_TIMEFRAMES)
        self.assertIn("1D", CLASSIC_PATTERN_TIMEFRAMES)


class UpdateStateTests(unittest.TestCase):
    def test_new_pattern_is_forming(self):
        state = {"schema_version": 2, "symbols": {}}
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        candidates = [{"type": "double_top", "subtype": "reversal", "direction": "bearish",
                       "pivots": [(0, 100.0), (10, 100.0)], "trendlines": [],
                       "boundary": {"upper": 100.0, "lower": 95.0},
                       "breakout_level": 95.0, "retest_level": 95.0, "measured_move": 5.0}]
        patterns, presentation, state = update_patterns_for_symbol_tf("w20", "4H", df, candidates, state)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["status"], STATUS_FORMING)
        self.assertIsNotNone(patterns[0]["created_at"])

    def test_status_persists_across_recalculation(self):
        state = {"schema_version": 2, "symbols": {}}
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        candidates = [{"type": "double_top", "subtype": "reversal", "direction": "bearish",
                       "pivots": [(0, 100.0), (10, 100.0)], "trendlines": [],
                       "boundary": {"upper": 100.0, "lower": 95.0},
                       "breakout_level": 95.0, "retest_level": 95.0, "measured_move": 5.0}]
        patterns, _, state = update_patterns_for_symbol_tf("w20", "4H", df, candidates, state)
        pid = patterns[0]["id"]
        self.assertEqual(patterns[0]["status"], STATUS_FORMING)
        patterns2, _, state2 = update_patterns_for_symbol_tf("w20", "4H", df, candidates, state)
        p2 = [p for p in patterns2 if p["id"] == pid][0]
        self.assertEqual(p2["status"], STATUS_FORMING)
        self.assertEqual(p2["created_at"], patterns[0]["created_at"])

    def test_no_duplicates(self):
        state = {"schema_version": 2, "symbols": {}}
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        cand = {"type": "double_top", "subtype": "reversal", "direction": "bearish",
                "pivots": [(0, 100.0), (10, 100.0)], "trendlines": [],
                "boundary": {"upper": 100.0, "lower": 95.0},
                "breakout_level": 95.0, "retest_level": 95.0, "measured_move": 5.0}
        patterns1, _, state1 = update_patterns_for_symbol_tf("w20", "4H", df, [cand], state)
        patterns2, _, state2 = update_patterns_for_symbol_tf("w20", "4H", df, [cand], state1)
        ids = [p["id"] for p in patterns2]
        self.assertEqual(len(ids), len(set(ids)))

    def test_symbol_isolation(self):
        state = {"schema_version": 2, "symbols": {}}
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        cand = {"type": "double_top", "subtype": "reversal", "direction": "bearish",
                "pivots": [(0, 100.0), (10, 100.0)], "trendlines": [],
                "boundary": {"upper": 100.0, "lower": 95.0},
                "breakout_level": 95.0, "retest_level": 95.0, "measured_move": 5.0}
        patterns_w20, _, state = update_patterns_for_symbol_tf("w20", "4H", df, [cand], state)
        patterns_us500, _, _ = update_patterns_for_symbol_tf("us500", "4H", df, [cand], state)
        self.assertEqual(len(patterns_w20), 1)
        self.assertEqual(len(patterns_us500), 1)
        self.assertNotEqual(patterns_w20[0]["id"], patterns_us500[0]["id"])

    def test_max_patterns_limit(self):
        state = {"schema_version": 2, "symbols": {}}
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        cand = {"type": "double_top", "subtype": "reversal", "direction": "bearish",
                "pivots": [(0, 100.0), (10, 100.0)], "trendlines": [],
                "boundary": {"upper": 100.0, "lower": 95.0},
                "breakout_level": 95.0, "retest_level": 95.0, "measured_move": 5.0}
        candidates = [dict(cand) for _ in range(7)]
        patterns, _, state = update_patterns_for_symbol_tf("w20", "4H", df, candidates, state)
        active = [p for p in patterns if p["status"] in (STATUS_FORMING, STATUS_CONFIRMED, STATUS_BREAKOUT, STATUS_RETEST)]
        self.assertLessEqual(len(active), CLASSIC_MAX_PATTERNS_PER_TF)


class DailyOneDMappingTests(unittest.TestCase):
    def test_timeframe_mapping(self):
        self.assertIn("1D", CLASSIC_PATTERN_TIMEFRAMES)


class BackwardCompatibilityTests(unittest.TestCase):
    def test_presentation_has_old_fields(self):
        state = {"schema_version": 2, "symbols": {}}
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(50)])
        candidates = [{"type": "double_top", "subtype": "reversal", "direction": "bearish",
                       "pivots": [(0, 100.0), (10, 100.0)], "trendlines": [],
                       "boundary": {"upper": 100.0, "lower": 95.0},
                       "breakout_level": 95.0, "retest_level": 95.0, "measured_move": 5.0}]
        _, presentation, _ = update_patterns_for_symbol_tf("w20", "4H", df, candidates, state)
        sym_patterns = presentation["symbols"]["w20"]
        self.assertTrue(len(sym_patterns) > 0)
        p = sym_patterns[0]
        self.assertIn("name", p)
        self.assertIn("direction", p)
        self.assertIn("bar", p)
        self.assertIn("time", p)
        self.assertIn("price", p)
        self.assertIn("status", p)
        self.assertIn("id", p)


if __name__ == "__main__":
    unittest.main()