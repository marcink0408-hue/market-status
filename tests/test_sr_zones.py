import unittest
import pandas as pd
from analysis.sr_zones import (
    detect_swings,
    group_swings_into_zones,
    rank_zones,
    filter_top_zones,
    match_multitf_zones,
    compute_zones_for_symbol,
    validate_zones,
    zones_for_chart,
)
from config import SWING_CONFIRMATION_BARS


def make_df(prices):
    index = pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC")
    return pd.DataFrame(prices, columns=["open", "high", "low", "close"], index=index)


class SwingDetectionTests(unittest.TestCase):
    def test_swing_high_confirmed_only_after_right_bars(self):
        prices = [
            (100, 101, 99, 100), (100, 102, 99, 101), (100, 103, 99, 102),
            (100, 104, 99, 103), (100, 110, 99, 105),
            (100, 106, 99, 104), (100, 105, 99, 103), (100, 104, 99, 102),
            (100, 103, 99, 101), (100, 102, 99, 100),
        ]
        df = make_df(prices)
        swings = detect_swings(df, "4H", "test")
        highs = [s for s in swings if s["type"] == "HIGH"]
        self.assertTrue(any(s["price"] == 110.0 for s in highs))
        self.assertTrue(all(s["confirmed"] for s in swings))

    def test_no_lookahead_last_bars_not_swings(self):
        prices = [(100 + i, 105 + i, 99 + i, 100 + i) for i in range(20)]
        df = make_df(prices)
        swings = detect_swings(df, "4H", "test")
        last_idx = len(df) - 1
        for s in swings:
            self.assertLess(s["bar_index"], last_idx - SWING_CONFIRMATION_BARS + 1)

    def test_insufficient_data_returns_empty(self):
        df = make_df([(100, 101, 99, 100)] * 5)
        swings = detect_swings(df, "4H", "test")
        self.assertEqual(swings, [])

    def test_swing_low_detected(self):
        prices = [
            (100, 101, 100, 100), (100, 102, 98, 100), (100, 103, 97, 100),
            (100, 104, 96, 100), (100, 105, 90, 100),
            (100, 104, 94, 100), (100, 103, 93, 100), (100, 102, 92, 100),
            (100, 101, 91, 100), (100, 100, 90, 100),
        ]
        df = make_df(prices)
        swings = detect_swings(df, "4H", "test")
        lows = [s for s in swings if s["type"] == "LOW"]
        self.assertTrue(any(s["price"] == 90.0 for s in lows))


class ZoneGroupingTests(unittest.TestCase):
    def test_swings_grouped_by_atr_tolerance(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(30)])
        swings = detect_swings(df, "4H", "test")
        atr = 1.0
        zones = group_swings_into_zones(swings, df, atr, current_price=100.0)
        self.assertIsInstance(zones, list)
        for z in zones:
            self.assertIn(z["type"], ("SUPPORT", "RESISTANCE"))
            self.assertGreater(z["upper"], z["lower"])
            self.assertIsInstance(z["reaction_count"], int)
            self.assertGreaterEqual(z["reaction_count"], 1)

    def test_zone_has_required_fields(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(30)])
        swings = detect_swings(df, "4H", "test")
        zones = group_swings_into_zones(swings, df, 1.0, current_price=100.0)
        for z in zones:
            for key in ("id", "type", "lower", "upper", "center", "reaction_count",
                         "interval", "symbol", "age_bars", "distance_from_price",
                         "rank_score", "rank_position", "status"):
                self.assertIn(key, z)

    def test_empty_swings_return_empty_zones(self):
        zones = group_swings_into_zones([], None, 1.0, current_price=100.0)
        self.assertEqual(zones, [])


class RankingTests(unittest.TestCase):
    def test_ranking_is_deterministic(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(30)])
        swings = detect_swings(df, "4H", "test")
        zones = group_swings_into_zones(swings, df, 1.0, current_price=100.0)
        ranked1 = rank_zones([dict(z) for z in zones], 100.0, 1.0)
        ranked2 = rank_zones([dict(z) for z in zones], 100.0, 1.0)
        self.assertEqual([z["rank_score"] for z in ranked1], [z["rank_score"] for z in ranked2])

    def test_rank_positions_unique(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(30)])
        swings = detect_swings(df, "4H", "test")
        zones = group_swings_into_zones(swings, df, 1.0, current_price=100.0)
        ranked = rank_zones(zones, 100.0, 1.0)
        positions = [z["rank_position"] for z in ranked]
        self.assertEqual(positions, sorted(positions))


class FilterTopZonesTests(unittest.TestCase):
    def test_max_2_above_and_2_below(self):
        zones = []
        for i in range(4):
            zones.append({"type": "RESISTANCE", "center": 110 + i, "lower": 109 + i, "upper": 111 + i, "rank_score": 10.0})
        for i in range(3):
            zones.append({"type": "SUPPORT", "center": 90 - i, "lower": 89 - i, "upper": 91 - i, "rank_score": 10.0})
        result = filter_top_zones(zones, 100.0)
        above = [z for z in result if z["center"] > 100]
        below = [z for z in result if z["center"] < 100]
        self.assertLessEqual(len(above), 2)
        self.assertLessEqual(len(below), 2)


class MultitfTests(unittest.TestCase):
    def test_match_multitf_requires_overlap(self):
        zones_by_tf = {
            "4H": [{"id": "z1", "type": "RESISTANCE", "lower": 100.0, "upper": 102.0, "rank_score": 10.0, "reaction_count": 2, "symbol": "test", "age_bars": 0}],
            "1D": [{"id": "z2", "type": "RESISTANCE", "lower": 101.0, "upper": 103.0, "rank_score": 10.0, "reaction_count": 2, "symbol": "test", "age_bars": 0}],
        }
        atr_by_tf = {"4H": 1.0, "1D": 1.0}
        result = match_multitf_zones(zones_by_tf, atr_by_tf)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "RESISTANCE")

    def test_match_multitf_no_overlap(self):
        zones_by_tf = {
            "4H": [{"id": "z1", "type": "RESISTANCE", "lower": 100.0, "upper": 101.0, "rank_score": 10.0, "reaction_count": 2, "symbol": "test", "age_bars": 0}],
            "1D": [{"id": "z2", "type": "RESISTANCE", "lower": 110.0, "upper": 112.0, "rank_score": 10.0, "reaction_count": 2, "symbol": "test", "age_bars": 0}],
        }
        atr_by_tf = {"4H": 1.0, "1D": 1.0}
        result = match_multitf_zones(zones_by_tf, atr_by_tf)
        self.assertEqual(len(result), 0)


class ValidationTests(unittest.TestCase):
    def test_validate_zones_rejects_invalid(self):
        zones = [
            {"type": "SUPPORT", "lower": 100.0, "upper": 102.0, "center": 101.0},
            {"type": "BAD", "lower": 100.0, "upper": 102.0, "center": 101.0},
            {"type": "SUPPORT", "lower": 0.0, "upper": 102.0, "center": 51.0},
            {"type": "SUPPORT", "lower": 102.0, "upper": 100.0, "center": 101.0},
            {"type": "SUPPORT", "lower": None, "upper": 102.0, "center": 101.0},
        ]
        valid = validate_zones(zones)
        self.assertEqual(len(valid), 1)


class ComputeZonesTests(unittest.TestCase):
    def test_compute_zones_for_symbol_structure(self):
        df = make_df([(100 + i, 105 + i, 99 + i, 100 + i) for i in range(40)])
        data_by_tf = {
            "4H": {"df": df, "current_price": 100.0, "atr": 1.0},
            "1H": {"df": df, "current_price": 100.0, "atr": 0.5},
        }
        result = compute_zones_for_symbol(data_by_tf, "test")
        self.assertIn("4H", result)
        self.assertIn("1H", result)
        for tf, zones in result.items():
            if tf == "MULTITF":
                continue
            for z in zones:
                self.assertEqual(z["interval"], tf)
                self.assertEqual(z["symbol"], "test")


if __name__ == "__main__":
    unittest.main()