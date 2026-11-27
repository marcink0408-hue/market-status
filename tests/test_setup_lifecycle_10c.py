import unittest
import pandas as pd
import tempfile
from pathlib import Path
from analysis.setup_lifecycle import (
    SetupLifecycle,
    STATUS_AKTYWNY, STATUS_OCZEKUJĄCY, STATUS_POTWIERDZONY,
    STATUS_UNIEWAŻNIONY, STATUS_WYGASŁY,
)
from config import SETUP_EXPIRY_BARS, CONFIRMED_VALID_BARS
from datetime import datetime, timedelta, timezone


def make_4h_df(bars=50, base=100.0):
    index = pd.date_range("2026-01-01", periods=bars, freq="4h", tz="UTC")
    close = pd.Series([base + i * 0.1 for i in range(bars)], index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


def df_at(bar_index, base=100.0):
    return make_4h_df(bar_index + 1, base=base)


def make_1h_df(closes, now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    n = len(closes)
    index = [now - timedelta(hours=n - i) for i in range(n)]
    close = pd.Series(closes, index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=pd.DatetimeIndex(index))


def base_update(lifecycle, direction="LONG", readiness_pct=40,
                trigger_confirmed=False, blockers=None, bar_index=40,
                invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0):
    if blockers is None:
        blockers = []
    return lifecycle.update(
        direction=direction, readiness_pct=readiness_pct,
        trigger_confirmed=trigger_confirmed, blockers=blockers,
        invalidation_level=invalidation_level, entry=entry, stop=stop, target=target,
        df_4h=df_at(bar_index), current_bar_index=bar_index, data_fresh=True,
    )


class Expiry3BarsTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_expiry_after_3_bars(self):
        lifecycle = SetupLifecycle("test_expiry_3bars", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=40, bar_index=40)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        self.assertEqual(result["last_setup_bar_index"], 40)
        result = base_update(lifecycle, readiness_pct=40, bar_index=41)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = base_update(lifecycle, readiness_pct=40, bar_index=42)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = base_update(lifecycle, readiness_pct=40, bar_index=43)
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_expiry_not_before_3_bars(self):
        lifecycle = SetupLifecycle("test_expiry_not_before", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=40, bar_index=40)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = base_update(lifecycle, readiness_pct=40, bar_index=41)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = base_update(lifecycle, readiness_pct=40, bar_index=42)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = base_update(lifecycle, readiness_pct=40, bar_index=43)
        self.assertEqual(result["status"], STATUS_WYGASŁY)


class ExpiryConfirmedTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_confirmed_expiry_after_2_bars(self):
        lifecycle = SetupLifecycle("test_confirmed_expiry", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=40)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=41)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=42)
        self.assertEqual(result["status"], STATUS_WYGASŁY)


class NewSetupBarRuleTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_no_new_setup_on_same_bar_as_expiry(self):
        lifecycle = SetupLifecycle("test_no_same_bar", state_path=self.state_path)
        base_update(lifecycle, readiness_pct=40, bar_index=40)
        base_update(lifecycle, readiness_pct=40, bar_index=41)
        base_update(lifecycle, readiness_pct=40, bar_index=42)
        result = base_update(lifecycle, readiness_pct=40, bar_index=43)
        self.assertEqual(result["status"], STATUS_WYGASŁY)
        self.assertEqual(result["last_setup_bar_index"], 43)
        result = base_update(lifecycle, readiness_pct=40, bar_index=43)
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_new_setup_on_next_bar_after_expiry(self):
        lifecycle = SetupLifecycle("test_next_bar", state_path=self.state_path)
        base_update(lifecycle, readiness_pct=40, bar_index=40)
        base_update(lifecycle, readiness_pct=40, bar_index=41)
        base_update(lifecycle, readiness_pct=40, bar_index=42)
        base_update(lifecycle, readiness_pct=40, bar_index=43)
        result = base_update(lifecycle, readiness_pct=40, bar_index=44)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        self.assertEqual(result["last_setup_bar_index"], 44)


class StatusTransition10CTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_immediate_confirmed_when_readiness_80_and_trigger(self):
        lifecycle = SetupLifecycle("test_immediate_confirmed", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=85, trigger_confirmed=True, bar_index=40)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)

    def test_ready_55_without_trigger_is_oczekujacy(self):
        lifecycle = SetupLifecycle("test_oczekujacy", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=60, trigger_confirmed=False, bar_index=40)
        self.assertEqual(result["status"], STATUS_OCZEKUJĄCY)

    def test_ready_40_is_aktywny(self):
        lifecycle = SetupLifecycle("test_aktywny", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=40, trigger_confirmed=False, bar_index=40)
        self.assertEqual(result["status"], STATUS_AKTYWNY)

    def test_state_has_last_setup_bar_index(self):
        lifecycle = SetupLifecycle("test_state_field", state_path=self.state_path)
        result = base_update(lifecycle, readiness_pct=40, bar_index=40)
        self.assertIn("last_setup_bar_index", result)
        self.assertEqual(result["last_setup_bar_index"], 40)


class WeekendGapTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_gap_df(self, timestamps):
        index = pd.DatetimeIndex([pd.Timestamp(ts, tz="UTC") for ts in timestamps])
        n = len(index)
        close = pd.Series([100.0 + i * 0.1 for i in range(n)], index=index)
        return pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=index)

    def test_weekend_without_candles_does_not_increment(self):
        timestamps = [
            "2026-01-02T16:00:00Z",
            "2026-01-05T00:00:00Z",
            "2026-01-05T04:00:00Z",
            "2026-01-05T08:00:00Z",
        ]
        df = self._make_gap_df(timestamps)
        lifecycle = SetupLifecycle("test_weekend", state_path=self.state_path)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=0, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=1, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=2, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=3, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_irregular_intervals_do_not_affect_counting(self):
        timestamps = [
            "2026-01-02T16:00:00Z",
            "2026-01-02T20:00:00Z",
            "2026-01-03T02:00:00Z",
            "2026-01-03T06:00:00Z",
        ]
        df = self._make_gap_df(timestamps)
        lifecycle = SetupLifecycle("test_irregular", state_path=self.state_path)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=0, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=3, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_WYGASŁY)


class RestartPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_restart_preserves_expiry_counter(self):
        from analysis.setup_lifecycle import STATE_PATH
        import os

        df = make_4h_df(45)
        lifecycle1 = SetupLifecycle("test_restart_1", state_path=self.state_path)
        result = lifecycle1.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=40, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        created_at = lifecycle1.state["created_at"]

        result = lifecycle1.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=41, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)

        lifecycle2 = SetupLifecycle("test_restart_1", state_path=self.state_path)
        self.assertEqual(lifecycle2.state["created_at"], created_at)
        self.assertEqual(lifecycle2.state["status"], STATUS_AKTYWNY)

        result = lifecycle2.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=42, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)

        result = lifecycle2.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=43, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_terminal_status_persists_after_restart(self):
        from analysis.setup_lifecycle import STATE_PATH
        import os

        df = make_4h_df(45)
        lifecycle1 = SetupLifecycle("test_restart_terminal", state_path=self.state_path)
        result = lifecycle1.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=40, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        for bi in (41, 42, 43):
            result = lifecycle1.update(
                direction="LONG", readiness_pct=40, trigger_confirmed=False,
                blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
                df_4h=df, current_bar_index=bi, data_fresh=True,
            )
        self.assertEqual(result["status"], STATUS_WYGASŁY)

        lifecycle2 = SetupLifecycle("test_restart_terminal", state_path=self.state_path)
        self.assertEqual(lifecycle2.state["status"], STATUS_WYGASŁY)
        self.assertTrue(lifecycle2.is_terminal())


class MissingHistoryAndIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_insufficient_history_no_expiry_guessing(self):
        timestamps = ["2026-01-02T16:00:00Z"]
        index = pd.DatetimeIndex([pd.Timestamp(ts, tz="UTC") for ts in timestamps])
        df = pd.DataFrame({
            "open": [99.95], "high": [100.2], "low": [99.8], "close": [100.0],
        }, index=index)
        lifecycle = SetupLifecycle("test_no_history", state_path=self.state_path)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=0, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=0, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)

    def test_index_change_does_not_cause_expiry(self):
        timestamps = [
            "2026-01-02T16:00:00Z",
            "2026-01-02T20:00:00Z",
            "2026-01-03T00:00:00Z",
            "2026-01-03T04:00:00Z",
        ]
        index = pd.DatetimeIndex([pd.Timestamp(ts, tz="UTC") for ts in timestamps])
        close = pd.Series([100.0 + i * 0.1 for i in range(4)], index=index)
        df1 = pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=index)
        df2 = df1.reindex(index)

        lifecycle1 = SetupLifecycle("test_index_1", state_path=self.state_path)
        r1 = lifecycle1.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df1, current_bar_index=0, data_fresh=True,
        )
        self.assertEqual(r1["status"], STATUS_AKTYWNY)
        for bi in (1, 2, 3):
            r1 = lifecycle1.update(
                direction="LONG", readiness_pct=40, trigger_confirmed=False,
                blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
                df_4h=df1, current_bar_index=bi, data_fresh=True,
            )
        self.assertEqual(r1["status"], STATUS_WYGASŁY)

        from analysis.setup_lifecycle import STATE_PATH
        import os
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)

        lifecycle2 = SetupLifecycle("test_index_2", state_path=Path(self._tmpdir.name) / "setup_state_2.json")
        r2 = lifecycle2.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df2, current_bar_index=0, data_fresh=True,
        )
        self.assertEqual(r2["status"], STATUS_AKTYWNY)
        for bi in (1, 2, 3):
            r2 = lifecycle2.update(
                direction="LONG", readiness_pct=40, trigger_confirmed=False,
                blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
                df_4h=df2, current_bar_index=bi, data_fresh=True,
            )
        self.assertEqual(r2["status"], STATUS_WYGASŁY)


class InvalidationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_invalidation_records_last_setup_bar_index(self):
        df = make_4h_df(45)
        lifecycle = SetupLifecycle("test_invalidation_idx", state_path=self.state_path)
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=40, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        self.assertEqual(lifecycle.state["last_setup_bar_index"], 40)

        df_mod = df.copy()
        df_mod.iloc[-1, df_mod.columns.get_loc("close")] = 85.0
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df_mod, current_bar_index=42, data_fresh=True,
            df_1h=make_1h_df([100.0, 85.0]),
        )
        self.assertEqual(result["status"], STATUS_UNIEWAŻNIONY)
        self.assertEqual(result["last_setup_bar_index"], 42)


class DataFreshTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_data_fresh_false_does_not_change_status(self):
        df = make_4h_df(45)
        lifecycle = SetupLifecycle("test_data_fresh", state_path=self.state_path)
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=40, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        status_before = lifecycle.state["status"]

        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=41, data_fresh=False,
        )
        self.assertEqual(result["status"], status_before)
        self.assertIn("Dane nieaktualne lub niekompletne", result["conditions_missing"])


class UnclosedCandleTests(unittest.TestCase):
    FIXED_NOW = datetime.now(timezone.utc)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_df_with_unclosed(self, n_closed):
        """n_closed zamkniętych świec (z make_4h_df) + 1 niezamknięta na końcu."""
        df_closed = make_4h_df(n_closed)
        unclosed_ts = self.FIXED_NOW + timedelta(hours=1)
        close = pd.Series(
            [100.0 + i * 0.1 for i in range(n_closed + 1)],
            index=df_closed.index.append(pd.DatetimeIndex([unclosed_ts])),
        )
        return pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=close.index)

    def _update_with_unclosed(self, lifecycle, bar_index, readiness_pct=40,
                              trigger_confirmed=False):
        """bar_index = liczba zamkniętych świec; ostatnia pozycja to niezamknięta."""
        df = self._make_df_with_unclosed(bar_index)
        return lifecycle.update(
            direction="LONG", readiness_pct=readiness_pct,
            trigger_confirmed=trigger_confirmed, blockers=[],
            invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=bar_index, data_fresh=True,
        )

    def test_unclosed_candle_not_counted(self):
        lifecycle = SetupLifecycle("test_unclosed_1", state_path=self.state_path)
        result = self._update_with_unclosed(lifecycle, bar_index=1)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        self.assertEqual(result["last_setup_bar_index"], 0)
        result = self._update_with_unclosed(lifecycle, bar_index=2)
        self.assertEqual(result["status"], STATUS_AKTYWNY)

    def test_2_closed_1_unclosed_not_expired(self):
        lifecycle = SetupLifecycle("test_2closed_1unclosed", state_path=self.state_path)
        result = self._update_with_unclosed(lifecycle, bar_index=1)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = self._update_with_unclosed(lifecycle, bar_index=2)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = self._update_with_unclosed(lifecycle, bar_index=3)
        self.assertEqual(result["status"], STATUS_AKTYWNY)

    def test_3_closed_then_expired_with_unclosed_tail(self):
        lifecycle = SetupLifecycle("test_3closed_expired", state_path=self.state_path)
        result = self._update_with_unclosed(lifecycle, bar_index=1)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = self._update_with_unclosed(lifecycle, bar_index=2)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = self._update_with_unclosed(lifecycle, bar_index=3)
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        result = self._update_with_unclosed(lifecycle, bar_index=4)
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_confirmed_1_closed_1_unclosed_not_expired(self):
        lifecycle = SetupLifecycle("test_conf_1closed_1unclosed", state_path=self.state_path)
        result = self._update_with_unclosed(
            lifecycle, bar_index=1, readiness_pct=85, trigger_confirmed=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = self._update_with_unclosed(
            lifecycle, bar_index=2, readiness_pct=85, trigger_confirmed=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)

    def test_confirmed_2_closed_expired(self):
        lifecycle = SetupLifecycle("test_conf_2closed_expired", state_path=self.state_path)
        result = self._update_with_unclosed(
            lifecycle, bar_index=1, readiness_pct=85, trigger_confirmed=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = self._update_with_unclosed(
            lifecycle, bar_index=2, readiness_pct=85, trigger_confirmed=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        result = self._update_with_unclosed(
            lifecycle, bar_index=3, readiness_pct=85, trigger_confirmed=True,
        )
        self.assertEqual(result["status"], STATUS_WYGASŁY)

    def test_no_tz_info_not_assumed_closed(self):
        """Timestamp bez strefy czasowej nie jest automatycznie uznany za zamknięty."""
        index = pd.DatetimeIndex([
            pd.Timestamp("2026-06-15T08:00:00"),
            pd.Timestamp("2026-06-15T12:00:00"),
        ])
        close = pd.Series([100.0, 100.1], index=index)
        df = pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=index)
        lifecycle = SetupLifecycle("test_no_tz", state_path=self.state_path)
        closed = lifecycle._last_closed_bar_index(df, 1)
        self.assertIsNone(closed)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df, current_bar_index=1, data_fresh=True,
        )
        self.assertIsNone(result["status"])


class FailSafeAndMinusOneTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / "setup_state.json"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_unclosed_df(self, n=1):
        """DataFrame z n świecami, ostatnia niezamknięta (w przyszłości)."""
        now = datetime.now(timezone.utc)
        timestamps = [now.replace(tzinfo=None) + timedelta(hours=i * 4) for i in range(n)]
        index = pd.DatetimeIndex([pd.Timestamp(ts, tz="UTC") for ts in timestamps])
        close = pd.Series([100.0 + i * 0.1 for i in range(n)], index=index)
        return pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=index)

    def test_single_unclosed_candle_no_closed_index(self):
        # Test 1: jedna niezamknięta świeca — brak dostępnego zamkniętego indeksu.
        df = self._make_unclosed_df(1)
        lifecycle = SetupLifecycle("test_single_unclosed", state_path=self.state_path)
        closed = lifecycle._last_closed_bar_index(df, 0)
        self.assertIsNone(closed)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df, current_bar_index=0, data_fresh=True,
        )
        self.assertIsNone(result["status"])

    def test_timestamp_conversion_error_safe_none(self):
        # Test 3: błąd konwersji timestampu — bezpieczny brak indeksu.
        index = pd.Index(["not-a-timestamp", "also-not-a-timestamp"])
        close = pd.Series([100.0, 100.1], index=index)
        df = pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=index)
        lifecycle = SetupLifecycle("test_conv_error", state_path=self.state_path)
        closed = lifecycle._last_closed_bar_index(df, 0)
        self.assertIsNone(closed)
        closed = lifecycle._last_closed_bar_index(df, 1)
        self.assertIsNone(closed)

    def test_no_reliable_closed_candle_update_preserves_state(self):
        # Test 4: brak wiarygodnej zamkniętej świecy — update() nie zmienia istniejącego stanu setupu.
        df_closed = make_4h_df(5)
        lifecycle = SetupLifecycle("test_no_reliable", state_path=self.state_path)
        result_before = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df_closed, current_bar_index=4, data_fresh=True,
        )
        self.assertEqual(result_before["status"], STATUS_AKTYWNY)
        state_before = lifecycle.get_state()

        # Teraz brak wiarygodnej zamkniętej świecy (tylko niezamknięta).
        df_unclosed = self._make_unclosed_df(1)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df_unclosed, current_bar_index=0, data_fresh=True,
        )
        # Stan nie może ulec żadnej zmianie.
        state_after = lifecycle.get_state()
        self.assertEqual(state_before, state_after)
        self.assertEqual(result["status"], state_before["status"])
        self.assertEqual(result["created_at"], state_before["created_at"])
        self.assertEqual(result["setup_confirmed_at"], state_before["setup_confirmed_at"])
        self.assertEqual(result["last_setup_bar_index"], state_before["last_setup_bar_index"])
        self.assertEqual(result["updated_at"], state_before["updated_at"])

    def test_first_closed_after_gap_lifecycle_works(self):
        # Test 5: pierwsza zamknięta świeca po braku — cykl życia działa prawidłowo.
        lifecycle = SetupLifecycle("test_first_closed_after_gap", state_path=self.state_path)
        # Najpierw brak zamkniętej świecy (tylko niezamknięta).
        df_unclosed = self._make_unclosed_df(1)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df_unclosed, current_bar_index=0, data_fresh=True,
        )
        self.assertIsNone(result["status"])
        # Potem pojawiają się zamknięte świece (w przeszłości) — cykl życia startuje.
        df_closed = make_4h_df(5)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df_closed, current_bar_index=4, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        self.assertEqual(result["last_setup_bar_index"], 4)

    def test_no_minus_one_indexing(self):
        # Test 6: żaden przypadek nie indeksuje DataFrame przez -1.
        now = datetime.now(timezone.utc)
        # current_bar_index = 0, jedyna świeca niezamknięta → closed_bar_index = None, nie -1.
        index = pd.DatetimeIndex([pd.Timestamp(now.replace(tzinfo=None) + timedelta(hours=1), tz="UTC")])
        close = pd.Series([100.0], index=index)
        df = pd.DataFrame({
            "open": close - 0.05, "high": close + 0.2,
            "low": close - 0.2, "close": close,
        }, index=index)
        lifecycle = SetupLifecycle("test_no_minus_one", state_path=self.state_path)
        closed = lifecycle._last_closed_bar_index(df, 0)
        self.assertIsNone(closed)
        self.assertNotEqual(closed, -1)
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0,
            target=110.0, df_4h=df, current_bar_index=0, data_fresh=True,
        )
        self.assertIsNone(result["status"])
        # Nie może dojść do df_4h.index[-1] — brak crashu, brak zmiany stanu.


if __name__ == "__main__":
    unittest.main()
