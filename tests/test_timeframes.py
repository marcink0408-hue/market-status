import unittest
import pandas as pd

from analysis.chart_data import build_chart_payload
from analysis.decision import make_decision
from data.fetcher import build_daily_from_hourly, drop_incomplete_bar, resample_ohlc


def frame(hours=20, base=100.0):
    index = pd.date_range("2026-01-01", periods=hours, freq="h", tz="UTC")
    close = pd.Series([base + i * 0.1 for i in range(hours)], index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


class TimeframeDataTests(unittest.TestCase):
    def test_4h_is_built_from_1h_with_utc_boundaries(self):
        hourly = frame(11)
        result = resample_ohlc(hourly, 4, now="2026-01-01 08:30:00+00:00")
        self.assertEqual(list(result.index), [
            pd.Timestamp("2026-01-01 00:00:00+00:00"),
            pd.Timestamp("2026-01-01 04:00:00+00:00"),
        ])
        self.assertAlmostEqual(result.iloc[0].open, hourly.iloc[0].open)
        self.assertAlmostEqual(result.iloc[0].high, hourly.iloc[:4].high.max())
        self.assertAlmostEqual(result.iloc[0].close, hourly.iloc[3].close)

    def test_incomplete_hour_is_removed(self):
        hourly = frame(3)
        result = drop_incomplete_bar(hourly, 1, now="2026-01-01 02:30:00+00:00")
        self.assertEqual(result.index[-1], pd.Timestamp("2026-01-01 01:00:00+00:00"))

    def test_daily_fallback_uses_exchange_session_and_excludes_current_day(self):
        hourly = frame(50)
        result = build_daily_from_hourly(
            hourly, timezone="Europe/Warsaw", now="2026-01-03 08:00:00+00:00",
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result.index[0], pd.Timestamp("2025-12-31 23:00:00+00:00"))
        self.assertAlmostEqual(result.iloc[0].open, hourly.iloc[0].open)

    def test_atr_is_null_when_it_cannot_be_calculated(self):
        result = make_decision(frame(10), {}, [], [])
        self.assertIsNone(result["atr"])


class MultiTimeframeDecisionTests(unittest.TestCase):
    def setUp(self):
        self.df = frame(30)
        self.renko = {
            "local_low": True, "local_high": False, "last_reversal": True,
            "direction": "up", "last_close": 100.0, "prev_leg_length": 4,
        }
        self.candles = [{"name": "Bullish Engulfing", "direction": "bullish", "strength": "strong"}]
        self.daily = {"decision": "LONG", "directional_scores": {"LONG": 80, "SHORT": 0}}
        self.hourly_conflict = {"decision": "SHORT", "directional_scores": {"LONG": 0, "SHORT": 80}}

    def test_4h_direction_survives_hourly_conflict(self):
        result = make_decision(
            self.df, self.renko, [], self.candles,
            daily_analysis=self.daily, hourly_analysis=self.hourly_conflict,
        )
        self.assertEqual(result["decision"], "LONG")
        self.assertEqual(result["timeframe_alignment"]["1H"]["status"], "conflict")
        self.assertEqual(result["timeframe_alignment"]["1D"]["status"], "confirms")
        self.assertEqual(result["confidence"], result["base_confidence"] + 12 - 8)
        self.assertEqual(result["levels_timeframe"], "4H")

    def test_no_setup_does_not_expose_reference_bias_as_main_decision(self):
        result = make_decision(
            self.df, {}, [], [], daily_analysis=self.daily,
            hourly_analysis=self.hourly_conflict,
        )
        self.assertEqual(result["decision"], "BRAK")
        self.assertEqual(result["timeframe_alignment"]["4H"]["bias"], "BRAK")

    def test_1h_levels_do_not_overwrite_4h_levels(self):
        hourly = {
            "decision": "LONG", "directional_scores": {"LONG": 70, "SHORT": 0},
            "levels_by_timeframe": {"1H": {
                "timeframe": "1H", "entry": 101.0, "stop": 99.0, "target": 104.0, "rr": 1.5,
            }},
        }
        result = make_decision(
            self.df, self.renko, [], self.candles,
            daily_analysis=self.daily, hourly_analysis=hourly,
        )
        # Poziomy 4H nie są nadpisywane przez 1H (brak mieszania interwałów)
        self.assertEqual(result["levels_timeframe"], "4H")
        self.assertEqual(result["levels_by_timeframe"], {"4H": result["levels_by_timeframe"]["4H"]})
        # MTF relacje są liczane osobno dla LONG i SHORT
        self.assertIn("mtf_long_adjustment", result)
        self.assertIn("mtf_short_adjustment", result)


class ChartPayloadTests(unittest.TestCase):
    def test_every_overlay_has_symbol_and_timeframe(self):
        df = frame(5)
        harmonic = {
            "name": "Butterfly", "direction": "bullish", "status": "completed",
            "lifecycle": "active", "time_D": str(df.index[-1]),
        }
        for role, index in zip("XABCD", range(5)):
            harmonic[role] = 100.0 + index
            harmonic[f"time_{role}"] = str(df.index[index])
        result = build_chart_payload(
            df, [], [harmonic], {"entry": 101, "stop": 99, "target": 104},
            symbol="gold", timeframe="4H",
        )
        self.assertEqual(result["symbol"], "gold")
        self.assertEqual(result["timeframe"], "4H")
        self.assertEqual(result["levels_timeframe"], "4H")
        self.assertEqual(result["harmonics"][0]["symbol"], "gold")
        self.assertEqual(result["harmonics"][0]["timeframe"], "4H")


if __name__ == "__main__":
    unittest.main()
