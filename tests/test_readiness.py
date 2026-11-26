import unittest
from analysis.readiness import (
    score_context_1d,
    score_structure_4h,
    score_sr_position,
    score_trigger,
    score_rr,
    evaluate_side,
    calculate_readiness,
    readiness_stage_label,
    is_entry_allowed,
)
from config import (
    READINESS_THRESHOLD_NO_DIRECTION,
    READINESS_THRESHOLD_OBSERVE,
    READINESS_THRESHOLD_PREPARATION,
    READINESS_THRESHOLD_ENTRY_CANDIDATE,
    MIN_RR,
)


class Context1DTests(unittest.TestCase):
    def test_context_1d_aligned_long(self):
        self.assertEqual(score_context_1d("LONG", "LONG"), 15)

    def test_context_1d_aligned_short(self):
        self.assertEqual(score_context_1d("SHORT", "SHORT"), 15)

    def test_context_1d_conflict(self):
        self.assertEqual(score_context_1d("SHORT", "LONG"), 0)
        self.assertEqual(score_context_1d("LONG", "SHORT"), 0)

    def test_context_1d_neutral(self):
        self.assertEqual(score_context_1d("neutral", "LONG"), 10)
        self.assertEqual(score_context_1d("neutral", "SHORT"), 10)

    def test_context_1d_none_brak(self):
        self.assertEqual(score_context_1d(None, "LONG"), 0)
        self.assertEqual(score_context_1d("BRAK", "LONG"), 0)


class Structure4HTests(unittest.TestCase):
    def test_structure_both_aligned(self):
        self.assertEqual(score_structure_4h(True, True, True), 25)

    def test_structure_only_renko(self):
        self.assertEqual(score_structure_4h(True, False, True), 12)

    def test_structure_only_harmonic(self):
        self.assertEqual(score_structure_4h(False, True, True), 12)

    def test_structure_none(self):
        self.assertEqual(score_structure_4h(False, False, True), 0)

    def test_structure_direction_mismatch(self):
        self.assertEqual(score_structure_4h(True, True, False), 0)


class SRPositionTests(unittest.TestCase):
    def test_sr_inside_support_long(self):
        self.assertEqual(score_sr_position(True, None, "LONG", "SUPPORT", 100.0, 1.0), 20)

    def test_sr_inside_resistance_short(self):
        self.assertEqual(score_sr_position(True, None, "SHORT", "RESISTANCE", 100.0, 1.0), 20)

    def test_sr_wrong_zone_type(self):
        self.assertEqual(score_sr_position(True, None, "LONG", "RESISTANCE", 100.0, 1.0), 0)
        self.assertEqual(score_sr_position(True, None, "SHORT", "SUPPORT", 100.0, 1.0), 0)

    def test_sr_near_zone_0_5_atr(self):
        self.assertEqual(score_sr_position(False, 0.5, "LONG", None, 100.0, 1.0), 10)

    def test_sr_near_zone_0_49_atr(self):
        self.assertEqual(score_sr_position(False, 0.49, "SHORT", None, 100.0, 1.0), 10)

    def test_sr_far_zone(self):
        self.assertEqual(score_sr_position(False, 0.51, "LONG", None, 100.0, 1.0), 0)
        self.assertEqual(score_sr_position(False, 1.0, "LONG", None, 100.0, 1.0), 0)

    def test_sr_no_atr(self):
        self.assertEqual(score_sr_position(False, 0.5, "LONG", None, 100.0, None), 0)


class TriggerTests(unittest.TestCase):
    def test_trigger_confirmed(self):
        self.assertEqual(score_trigger(True), 30)

    def test_trigger_not_confirmed(self):
        self.assertEqual(score_trigger(False), 0)


class RRTests(unittest.TestCase):
    def test_rr_above_min(self):
        self.assertEqual(score_rr(1.5), 10)
        self.assertEqual(score_rr(2.0), 10)

    def test_rr_below_min(self):
        self.assertEqual(score_rr(1.4), 0)
        self.assertEqual(score_rr(1.0), 0)

    def test_rr_none(self):
        self.assertEqual(score_rr(None), 0)


class EvaluateSideTests(unittest.TestCase):
    def test_evaluate_side_full_long(self):
        result = evaluate_side(
            "LONG",
            {"bias": "LONG"},
            {"renko_aligned": True, "harmonic_active": True, "direction_match": True},
            {"price_in_zone": True, "zone_type": "SUPPORT"},
            {"confirmed": True},
            {"rr": 2.0, "entry": 100.0, "stop": 95.0, "target": 110.0},
            100.0, 1.0,
        )
        self.assertEqual(result["readiness_pct"], 100)
        self.assertEqual(len(result["missing"]), 0)
        self.assertTrue(all(c["met"] for c in result["criteria"]))

    def test_evaluate_side_empty_long(self):
        result = evaluate_side(
            "LONG", None, None, None, None, None, 100.0, 1.0,
        )
        self.assertEqual(result["readiness_pct"], 0)
        self.assertEqual(len(result["missing"]), 5)

    def test_evaluate_side_partial(self):
        result = evaluate_side(
            "LONG",
            {"bias": "neutral"},
            {"renko_aligned": True, "harmonic_active": False, "direction_match": True},
            {"price_in_zone": False, "zone_distance_atr": 0.3, "zone_type": None},
            {"confirmed": False},
            {"rr": 1.0, "entry": 100.0, "stop": 95.0, "target": 101.0},
            100.0, 1.0,
        )
        self.assertEqual(result["readiness_pct"], 32)


class ReadinessStageLabelTests(unittest.TestCase):
    def test_stage_brak_kierunku(self):
        self.assertEqual(readiness_stage_label(0), "BRAK KIERUNKU")
        self.assertEqual(readiness_stage_label(29), "BRAK KIERUNKU")

    def test_stage_obserwuj(self):
        self.assertEqual(readiness_stage_label(30), "OBSERWUJ")
        self.assertEqual(readiness_stage_label(54), "OBSERWUJ")

    def test_stage_przygotowanie(self):
        self.assertEqual(readiness_stage_label(55), "PRZYGOTOWANIE")
        self.assertEqual(readiness_stage_label(79), "PRZYGOTOWANIE")

    def test_stage_kandydat(self):
        self.assertEqual(readiness_stage_label(80), "KANDYDAT DO WEJŚCIA")
        self.assertEqual(readiness_stage_label(100), "KANDYDAT DO WEJŚCIA")

    def test_stage_none(self):
        self.assertEqual(readiness_stage_label(None), "BRAK DANYCH")


class IsEntryAllowedTests(unittest.TestCase):
    def test_entry_allowed_high_no_blockers(self):
        self.assertTrue(is_entry_allowed(85, []))

    def test_entry_allowed_below_threshold(self):
        self.assertFalse(is_entry_allowed(79, []))

    def test_entry_allowed_with_blockers(self):
        self.assertFalse(is_entry_allowed(90, ["Brak potwierdzonego wyzwalacza 1H"]))

    def test_entry_allowed_none(self):
        self.assertFalse(is_entry_allowed(None, []))


class CalculateReadinessTests(unittest.TestCase):
    def _full_side_data(self, side_bias="LONG", structure_full=True, sr_in_zone=True,
                        trigger_confirmed=True, rr_val=2.0, zone_type="SUPPORT"):
        return {
            "context_1d": {"bias": side_bias, "note": "kontekst"},
            "structure_4h": {
                "renko_aligned": structure_full,
                "harmonic_active": structure_full,
                "direction_match": True,
                "note": "struktura",
            },
            "sr_position": {
                "price_in_zone": sr_in_zone,
                "zone_distance_atr": 0.0,
                "zone_type": zone_type,
                "note": "S/R",
            },
            "trigger": {"confirmed": trigger_confirmed, "trigger_level": 100.0, "note": "wyzwalacz"},
            "rr": {"rr": rr_val, "entry": 100.0, "stop": 95.0, "target": 110.0,
                   "invalidation_level": 94.0, "note": "RR"},
        }

    def test_long_full_readiness_100(self):
        result = calculate_readiness(
            "gold", "4H",
            self._full_side_data(), None,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertEqual(result["direction"], "LONG")
        self.assertEqual(result["readiness_pct"], 100)
        self.assertTrue(result["entry_allowed"])
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["entry"], 100.0)
        self.assertEqual(result["stop"], 95.0)

    def test_data_not_fresh_blocks(self):
        data = self._full_side_data()
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, False, False, False, False, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])
        self.assertIn("Dane nieaktualne lub niekompletne", result["blockers"])

    def test_invalidated_blocks(self):
        data = self._full_side_data()
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, True, False, False, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])
        self.assertIn("Scenariusz unieważniony", result["blockers"])

    def test_expired_blocks(self):
        data = self._full_side_data()
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, False, False, True, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])
        self.assertIn("Setup wygasł", result["blockers"])

    def test_invalid_sl_blocks(self):
        data = self._full_side_data()
        data["rr"]["stop"] = 105.0
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertFalse(result["entry_allowed"])
        self.assertIn("Nieprawidłowy poziom SL", result["blockers"])

    def test_null_values_for_missing(self):
        result = calculate_readiness(
            "gold", "4H", None, None,
            None, None, True, False, False, False, False,
        )
        self.assertIsNone(result["entry"])
        self.assertIsNone(result["stop"])
        self.assertIsNone(result["target"])
        self.assertIsNone(result["rr"])
        self.assertIsNone(result["trigger_level"])
        self.assertIsNone(result["invalidation_level"])

    def test_scores_contain_both_sides(self):
        data = self._full_side_data()
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertIn("LONG", result["scores"])
        self.assertIn("SHORT", result["scores"])
        self.assertEqual(result["scores"]["LONG"]["readiness_pct"], 100)
        self.assertEqual(result["scores"]["SHORT"]["readiness_pct"], 0)

    def test_schema_has_required_fields(self):
        data = self._full_side_data()
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, False, False, False, False,
            next_check_time="2026-11-27T10:00:00Z",
            expires_at="2026-11-28T10:00:00Z",
            data_as_of="2026-11-26T08:00:00Z",
        )
        required = [
            "symbol", "main_timeframe", "direction", "readiness_pct", "stage",
            "setup_status", "entry_allowed", "blockers", "criteria", "scores",
            "missing", "trigger_level", "invalidation_level", "entry", "stop",
            "target", "rr", "next_check_time", "expires_at", "data_as_of", "generated_at",
        ]
        for field in required:
            self.assertIn(field, result)
        self.assertEqual(result["symbol"], "gold")
        self.assertEqual(result["main_timeframe"], "4H")
        self.assertEqual(result["next_check_time"], "2026-11-27T10:00:00Z")
        self.assertEqual(result["expires_at"], "2026-11-28T10:00:00Z")
        self.assertEqual(result["data_as_of"], "2026-11-26T08:00:00Z")
        self.assertEqual(result["target"], 110.0)
        self.assertEqual(result["rr"], 2.0)

    def test_long_with_blocker_no_entry(self):
        data = self._full_side_data(trigger_confirmed=False)
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])
        self.assertIn("Brak potwierdzonego wyzwalacza 1H", result["blockers"])

    def test_rr_below_min_blocks_entry(self):
        data = self._full_side_data(rr_val=1.0)
        result = calculate_readiness(
            "gold", "4H", data, None,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])
        self.assertIn("RR poniżej 1.5 lub nieznane", result["blockers"])

    def test_both_sides_weak_brak_kierunku(self):
        result = calculate_readiness(
            "gold", "4H", None, None,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])

    def test_long_allowed_short_blocked(self):
        long_data = self._full_side_data()
        short_data = self._full_side_data(side_bias="SHORT", trigger_confirmed=False)
        result = calculate_readiness(
            "gold", "4H", long_data, short_data,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertEqual(result["direction"], "LONG")
        self.assertTrue(result["entry_allowed"])

    def test_both_strong_min_diff_not_met(self):
        long_data = self._full_side_data()
        short_data = self._full_side_data(side_bias="SHORT", zone_type="RESISTANCE")
        short_data["rr"]["stop"] = 105.0
        short_data["rr"]["target"] = 90.0
        short_data["rr"]["invalidation_level"] = 106.0
        result = calculate_readiness(
            "gold", "4H", long_data, short_data,
            100.0, 1.0, True, False, False, False, False,
        )
        self.assertEqual(result["direction"], "NONE")
        self.assertFalse(result["entry_allowed"])