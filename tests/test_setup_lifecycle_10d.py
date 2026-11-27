import unittest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from analysis.setup_lifecycle import (
    SetupLifecycle,
    STATUS_AKTYWNY, STATUS_OCZEKUJĄCY, STATUS_POTWIERDZONY,
    STATUS_UNIEWAŻNIONY, STATUS_WYGASŁY,
)
from config import SETUP_EXPIRY_BARS, CONFIRMED_VALID_BARS


def make_4h_df(bars=50, base=100.0):
    index = pd.date_range("2026-01-01", periods=bars, freq="4h", tz="UTC")
    close = pd.Series([base + i * 0.1 for i in range(bars)], index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


def df_at(bar_index, base=100.0):
    return make_4h_df(bar_index + 1, base=base)


def make_1h_df(closes, now=None, add_open=False, open_close=None):
    if now is None:
        now = datetime.now(timezone.utc)
    n = len(closes)
    index = [now - timedelta(hours=n - i) for i in range(n)]
    closes = list(closes)
    if add_open:
        index = index + [now]
        closes = closes + [open_close if open_close is not None else closes[-1] + 0.1]
    index = pd.DatetimeIndex(index)
    close = pd.Series(closes, index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


def base_update(lifecycle, direction="LONG", readiness_pct=40,
                trigger_confirmed=False, blockers=None, bar_index=40,
                invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
                df_1h=None, data_fresh=True):
    if blockers is None:
        blockers = []
    return lifecycle.update(
        direction=direction, readiness_pct=readiness_pct,
        trigger_confirmed=trigger_confirmed, blockers=blockers,
        invalidation_level=invalidation_level, entry=entry, stop=stop, target=target,
        df_4h=df_at(bar_index), current_bar_index=bar_index, df_1h=df_1h,
        data_fresh=data_fresh,
    )


class LifecycleSetupTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()


class Invalidation1HTests(LifecycleSetupTests):
    def test_invalidation_on_closed_1h_close_below_level(self):
        lifecycle = SetupLifecycle("test_1h_inval_long", state_path=self.state_path)
        base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=40,
                    invalidation_level=90.0)
        self.assertEqual(lifecycle.state["status"], STATUS_POTWIERDZONY)
        df_1h = make_1h_df([100.0, 85.0])
        result = base_update(lifecycle, readiness_pct=40, bar_index=41, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        self.assertIn("1H", result["conditions_missing"][0])

    def test_open_1h_candle_does_not_invalidate(self):
        lifecycle = SetupLifecycle("test_1h_open", state_path=self.state_path)
        base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=40,
                    invalidation_level=90.0)
        df_1h = make_1h_df([100.0], add_open=True, open_close=85.0)
        result = base_update(lifecycle, readiness_pct=40, bar_index=41, df_1h=df_1h)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_4h_close_does_not_substitute_1h_close(self):
        lifecycle = SetupLifecycle("test_4h_not_1h", state_path=self.state_path)
        base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=40,
                    invalidation_level=90.0)
        df_4h_breach = df_at(41, base=100.0)
        df_4h_breach.iloc[-1, df_4h_breach.columns.get_loc("close")] = 85.0
        df_1h = make_1h_df([100.0])
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False, blockers=[],
            invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df_4h_breach, current_bar_index=41, df_1h=df_1h, data_fresh=True,
        )
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_no_reliable_1h_closed_no_invalidation(self):
        lifecycle = SetupLifecycle("test_1h_none", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=40, bar_index=40,
                             invalidation_level=90.0, df_1h=None)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_no_tz_or_bad_timestamp_fail_safe(self):
        lifecycle = SetupLifecycle("test_1h_notz", state_path=self.state_path)
        base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=40,
                    invalidation_level=90.0)
        index = pd.DatetimeIndex([pd.Timestamp("2026-06-15T08:00:00"),
                                  pd.Timestamp("2026-06-15T09:00:00")])
        close = pd.Series([100.0, 85.0], index=index)
        df_1h = pd.DataFrame({"open": close - 0.05, "high": close + 0.2,
                              "low": close - 0.2, "close": close}, index=index)
        result = base_update(lifecycle, readiness_pct=40, bar_index=41, df_1h=df_1h)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_long_and_short_invalid_directions(self):
        lf_path = Path(self._tmpdir.name) / "setup_state_1h_long.json"
        sf_path = Path(self._tmpdir.name) / "setup_state_1h_short.json"
        lf2_path = Path(self._tmpdir.name) / "setup_state_1h_long_safe.json"
        lf = SetupLifecycle("test_1h_long", state_path=lf_path)
        base_update(lf, readiness_pct=85, trigger_confirmed=True, bar_index=40,
                    invalidation_level=90.0)
        r = base_update(lf, readiness_pct=40, bar_index=41,
                        df_1h=make_1h_df([100.0, 85.0]), invalidation_level=90.0)
        self.assertEqual(r["status"], STATUS_UNIEWAŻNIONY)

        sf = SetupLifecycle("test_1h_short", state_path=sf_path)
        base_update(sf, direction="SHORT", readiness_pct=85, trigger_confirmed=True,
                    bar_index=40, invalidation_level=110.0)
        r = base_update(sf, direction="SHORT", readiness_pct=40, bar_index=41,
                        df_1h=make_1h_df([100.0, 115.0]), invalidation_level=110.0)
        self.assertEqual(r["status"], STATUS_UNIEWAŻNIONY)

        lf2 = SetupLifecycle("test_1h_long_safe", state_path=lf2_path)
        base_update(lf2, readiness_pct=85, trigger_confirmed=True, bar_index=40,
                    invalidation_level=90.0)
        r = base_update(lf2, readiness_pct=40, bar_index=41,
                        df_1h=make_1h_df([100.0, 95.0]), invalidation_level=90.0)
        self.assertNotEqual(r["status"], STATUS_UNIEWAŻNIONY)



    def test_invalidation_1h_more_rows_than_4h(self):
        """df_1h ma więcej wierszy niż df_4h; zamknięcie 1H poza zakresem indeksu 4H unieważnia."""
        lifecycle = SetupLifecycle("test_1h_more_rows", state_path=self.state_path)
        df_4h_small = df_at(3)
        df_1h_big = make_1h_df([100.0] * 19 + [85.0])
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True, blockers=[],
            invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df_4h_small, current_bar_index=3, df_1h=df_1h_big, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False, blockers=[],
            invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df_4h_small, current_bar_index=3, df_1h=df_1h_big, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        self.assertIn("1H", result["conditions_missing"][0])


class ExpiryRegressionTests(LifecycleSetupTests):
    def test_4h_expiry_still_works_after_1h_change(self):
        lifecycle = SetupLifecycle("test_expiry_reg", state_path=self.state_path)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, readiness_pct=40, bar_index=40, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        for bi in (41, 42):
            result = base_update(lifecycle, readiness_pct=40, bar_index=bi, df_1h=df_1h)
            self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = base_update(lifecycle, readiness_pct=40, bar_index=43, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_confirmed_4h_expiry_still_works(self):
        lifecycle = SetupLifecycle("test_conf_exp_reg", state_path=self.state_path)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True,
                             bar_index=40, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True,
                             bar_index=41, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True,
                             bar_index=42, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_WYGASŁY)


class DirectionChangeTests(LifecycleSetupTests):
    def _active_setup(self, lifecycle, direction="LONG", bar_index=40):
        df_1h = make_1h_df([100.0, 100.1])
        return base_update(lifecycle, direction=direction, readiness_pct=85,
                           trigger_confirmed=True, bar_index=bar_index,
                           invalidation_level=90.0 if direction == "LONG" else 110.0,
                           df_1h=df_1h)

    def test_long_to_short_invalidates(self):
        lifecycle = SetupLifecycle("test_dc_l2s", state_path=self.state_path)
        self._active_setup(lifecycle, "LONG", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction="SHORT", readiness_pct=85,
                             trigger_confirmed=True, bar_index=41,
                             invalidation_level=110.0, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        self.assertIn("LONG -> SHORT", result["conditions_missing"][0])

    def test_short_to_long_invalidates(self):
        lifecycle = SetupLifecycle("test_dc_s2l", state_path=self.state_path)
        self._active_setup(lifecycle, "SHORT", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction="LONG", readiness_pct=85,
                             trigger_confirmed=True, bar_index=41,
                             invalidation_level=90.0, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        self.assertIn("SHORT -> LONG", result["conditions_missing"][0])



    def test_long_to_none_does_not_invalidate(self):
        lifecycle = SetupLifecycle("test_dc_l2none", state_path=self.state_path)
        self._active_setup(lifecycle, "LONG", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction=None, readiness_pct=40,
                             trigger_confirmed=False, bar_index=41,
                             invalidation_level=90.0, df_1h=df_1h)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_short_to_none_does_not_invalidate(self):
        lifecycle = SetupLifecycle("test_dc_s2none", state_path=self.state_path)
        self._active_setup(lifecycle, "SHORT", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction=None, readiness_pct=40,
                             trigger_confirmed=False, bar_index=41,
                             invalidation_level=110.0, df_1h=df_1h)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_long_to_brak_does_not_invalidate(self):
        lifecycle = SetupLifecycle("test_dc_l2brak", state_path=self.state_path)
        self._active_setup(lifecycle, "LONG", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction="BRAK", readiness_pct=40,
                             trigger_confirmed=False, bar_index=41,
                             invalidation_level=90.0, df_1h=df_1h)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_short_to_brak_does_not_invalidate(self):
        lifecycle = SetupLifecycle("test_dc_s2brak", state_path=self.state_path)
        self._active_setup(lifecycle, "SHORT", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction="BRAK", readiness_pct=40,
                             trigger_confirmed=False, bar_index=41,
                             invalidation_level=110.0, df_1h=df_1h)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_data_fresh_false_no_direction_invalidation(self):
        lifecycle = SetupLifecycle("test_dc_stale", state_path=self.state_path)
        self._active_setup(lifecycle, "LONG", 40)
        df_1h = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction="SHORT", readiness_pct=85,
                             trigger_confirmed=True, bar_index=41,
                             invalidation_level=110.0, df_1h=df_1h, data_fresh=False)
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_terminal_status_not_re_invalidated(self):
        lifecycle = SetupLifecycle("test_dc_terminal", state_path=self.state_path)
        self._active_setup(lifecycle, "LONG", 40)
        df_1h = make_1h_df([100.0, 85.0])
        result = base_update(lifecycle, readiness_pct=40, bar_index=41, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        df_1h2 = make_1h_df([100.0, 100.1])
        result = base_update(lifecycle, direction="SHORT", readiness_pct=85,
                             trigger_confirmed=True, bar_index=42,
                             invalidation_level=110.0, df_1h=df_1h2)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_no_new_setup_on_same_bar_after_direction_invalidation(self):
        lifecycle = SetupLifecycle("test_dc_same_bar", state_path=self.state_path)
        self._active_setup(lifecycle, "LONG", 40)
        df_1h = make_1h_df([100.0, 85.0])
        result = base_update(lifecycle, readiness_pct=40, bar_index=41, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        self.assertEqual(result["last_setup_bar_index"], 41)
        result = base_update(lifecycle, direction="SHORT", readiness_pct=85,
                             trigger_confirmed=True, bar_index=41,
                             invalidation_level=110.0, df_1h=df_1h)
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)


if __name__ == "__main__":
    unittest.main()

