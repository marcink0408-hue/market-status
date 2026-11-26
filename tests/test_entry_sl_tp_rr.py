import unittest
from analysis.analyzer import calculate_sl, calculate_tp, calculate_rr, fallback_tp_from_levels


class CalculateSLTests(unittest.TestCase):
    def test_long_sl_below_support_with_buffer(self):
        sr_zones = [{"type": "SUPPORT", "lower": 98.0, "upper": 99.0, "center": 98.5}]
        sl = calculate_sl("LONG", 105.0, sr_zones, 100.0, 1.0 * 0.25)
        self.assertEqual(sl, 97.75)

    def test_short_sl_above_resistance_with_buffer(self):
        sr_zones = [{"type": "RESISTANCE", "lower": 106.0, "upper": 107.0, "center": 106.5}]
        sl = calculate_sl("SHORT", 105.0, sr_zones, 100.0, 1.0 * 0.25)
        self.assertEqual(sl, 107.25)

    def test_long_sl_none_when_no_support_zone(self):
        sl = calculate_sl("LONG", 105.0, [], 100.0, 0.25)
        self.assertIsNone(sl)

    def test_short_sl_none_when_no_resistance_zone(self):
        sl = calculate_sl("SHORT", 105.0, [], 100.0, 0.25)
        self.assertIsNone(sl)

    def test_long_sl_none_when_entry_none(self):
        sl = calculate_sl("LONG", None, [{"type": "SUPPORT", "lower": 98.0, "upper": 99.0}], 100.0, 0.25)
        self.assertIsNone(sl)

    def test_short_sl_none_when_invalidation_buffer_none(self):
        sl = calculate_sl("SHORT", 105.0, [{"type": "RESISTANCE", "lower": 106.0, "upper": 107.0}], 100.0, None)
        self.assertIsNone(sl)


class CalculateTPTests(unittest.TestCase):
    def test_long_tp_from_nearest_resistance_above(self):
        sr_zones = [
            {"type": "RESISTANCE", "lower": 110.0, "upper": 111.0, "center": 110.5},
            {"type": "RESISTANCE", "lower": 120.0, "upper": 121.0, "center": 120.5},
        ]
        tp = calculate_tp("LONG", 100.0, sr_zones)
        self.assertEqual(tp, 110.5)

    def test_short_tp_from_nearest_support_below(self):
        sr_zones = [
            {"type": "SUPPORT", "lower": 89.0, "upper": 90.0, "center": 89.5},
            {"type": "SUPPORT", "lower": 80.0, "upper": 81.0, "center": 80.5},
        ]
        tp = calculate_tp("SHORT", 100.0, sr_zones)
        self.assertEqual(tp, 89.5)

    def test_long_tp_none_when_no_resistance(self):
        tp = calculate_tp("LONG", 100.0, [])
        self.assertIsNone(tp)

    def test_short_tp_none_when_no_support(self):
        tp = calculate_tp("SHORT", 100.0, [])
        self.assertIsNone(tp)

    def test_long_tp_none_when_entry_none(self):
        tp = calculate_tp("LONG", None, [{"type": "RESISTANCE", "lower": 110.0, "upper": 111.0}])
        self.assertIsNone(tp)

    def test_tp_is_center_not_edge(self):
        sr_zones = [{"type": "RESISTANCE", "lower": 110.0, "upper": 112.0, "center": 111.0}]
        tp = calculate_tp("LONG", 100.0, sr_zones)
        self.assertEqual(tp, 111.0)


class CalculateRRTests(unittest.TestCase):
    def test_rr_exactly_1_5(self):
        rr, note = calculate_rr("LONG", 100.0, 95.0, 107.5)
        self.assertEqual(rr, 1.5)
        self.assertIn("RR: 1.5", note)

    def test_rr_above_1_5(self):
        rr, note = calculate_rr("LONG", 100.0, 95.0, 110.0)
        self.assertEqual(rr, 2.0)

    def test_rr_below_1_5(self):
        rr, note = calculate_rr("LONG", 100.0, 95.0, 106.0)
        self.assertEqual(rr, 1.2)

    def test_rr_short_above_1_5(self):
        rr, note = calculate_rr("SHORT", 100.0, 105.0, 95.0)
        self.assertEqual(rr, 1.0)

    def test_rr_none_when_entry_none(self):
        rr, note = calculate_rr("LONG", None, 95.0, 110.0)
        self.assertIsNone(rr)

    def test_rr_none_when_sl_none(self):
        rr, note = calculate_rr("LONG", 100.0, None, 110.0)
        self.assertIsNone(rr)

    def test_rr_none_when_tp_none(self):
        rr, note = calculate_rr("LONG", 100.0, 95.0, None)
        self.assertIsNone(rr)

    def test_rr_long_invalid_sl_above_entry(self):
        rr, note = calculate_rr("LONG", 100.0, 105.0, 110.0)
        self.assertIsNone(rr)

    def test_rr_short_invalid_sl_below_entry(self):
        rr, note = calculate_rr("SHORT", 100.0, 95.0, 90.0)
        self.assertIsNone(rr)


class FallbackTPTests(unittest.TestCase):
    def test_fallback_tp_long_when_target_above_entry(self):
        dec_levels = {"entry": 100.0, "stop": 95.0, "target": 110.0}
        tp = fallback_tp_from_levels("LONG", 100.0, dec_levels)
        self.assertEqual(tp, 110.0)

    def test_fallback_tp_short_when_target_below_entry(self):
        dec_levels = {"entry": 100.0, "stop": 105.0, "target": 90.0}
        tp = fallback_tp_from_levels("SHORT", 100.0, dec_levels)
        self.assertEqual(tp, 90.0)

    def test_fallback_tp_long_rejected_when_target_below_entry(self):
        dec_levels = {"entry": 100.0, "stop": 95.0, "target": 99.0}
        tp = fallback_tp_from_levels("LONG", 100.0, dec_levels)
        self.assertIsNone(tp)

    def test_fallback_tp_none_when_entry_none(self):
        tp = fallback_tp_from_levels("LONG", None, {"entry": 100.0, "stop": 95.0, "target": 110.0})
        self.assertIsNone(tp)

    def test_fallback_tp_none_when_missing_levels(self):
        tp = fallback_tp_from_levels("LONG", 100.0, {"entry": 100.0})
        self.assertIsNone(tp)


if __name__ == "__main__":
    unittest.main()