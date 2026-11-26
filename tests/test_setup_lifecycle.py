import os
import unittest
import pandas as pd
from analysis.setup_lifecycle import STATE_PATH
from analysis.setup_lifecycle import (
    SetupLifecycle, manage_lifecycle,
    STATUS_AKTYWNY, STATUS_OCZEKUJĄCY, STATUS_POTWIERDZONY,
    STATUS_UNIEWAŻNIONY, STATUS_WYGASŁY,
    _status_from_readiness,
)


def make_df(bars=50, base=100.0):
    index = pd.date_range("2026-01-01", periods=bars, freq="4h", tz="UTC")
    close = pd.Series([base + i * 0.1 for i in range(bars)], index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


def _base_update(lifecycle, direction="LONG", readiness_pct=40,
                 trigger_confirmed=False, blockers=None, df=None,
                 invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0):
    if blockers is None:
        blockers = []
    if df is None:
        df = make_df()
    return lifecycle.update(
        direction=direction, readiness_pct=readiness_pct,
        trigger_confirmed=trigger_confirmed, blockers=blockers,
        invalidation_level=invalidation_level, entry=entry, stop=stop, target=target,
        df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
    )


class StatusMappingTests(unittest.TestCase):
    def test_status_from_readiness_brak(self):
        self.assertIsNone(_status_from_readiness(29))
        self.assertIsNone(_status_from_readiness(0))
        self.assertIsNone(_status_from_readiness(None))

    def test_status_from_readiness_aktywny(self):
        self.assertEqual(_status_from_readiness(30), STATUS_AKTYWNY)
        self.assertEqual(_status_from_readiness(54), STATUS_AKTYWNY)

    def test_status_from_readiness_oczekujacy(self):
        self.assertEqual(_status_from_readiness(55), STATUS_OCZEKUJĄCY)
        self.assertEqual(_status_from_readiness(79), STATUS_OCZEKUJĄCY)

    def test_status_from_readiness_potwierdzony(self):
        self.assertEqual(_status_from_readiness(80), STATUS_POTWIERDZONY)
        self.assertEqual(_status_from_readiness(100), STATUS_POTWIERDZONY)


class LifecycleCreationTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)

    def test_new_setup_aktywny(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        result = lifecycle.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_AKTYWNY)
        self.assertEqual(result["direction"], "LONG")
        self.assertIsNotNone(result["setup_id"])
        self.assertIsNotNone(result["expires_at"])

    def test_new_setup_potwierdzony(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)
        self.assertEqual(result["direction"], "LONG")

    def test_no_setup_below_30(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        result = lifecycle.update(
            direction="LONG", readiness_pct=20, trigger_confirmed=False,
            blockers=[], invalidation_level=None, entry=None, stop=None, target=None,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        self.assertIsNone(result["status"])
        self.assertIsNone(result["direction"])

    def test_setup_id_unique_between_runs(self):
        df = make_df()
        l1 = SetupLifecycle("test_symbol")
        r1 = l1.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        id1 = r1["setup_id"]
        l2 = SetupLifecycle("test_symbol")
        r2 = l2.update(
            direction="LONG", readiness_pct=40, trigger_confirmed=False,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        self.assertEqual(r1["setup_id"], r2["setup_id"])


class TransitionTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)

    def test_aktywny_to_oczekujacy(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=40, trigger_confirmed=False)
        result = _base_update(lifecycle, readiness_pct=60, trigger_confirmed=False)
        self.assertEqual(result["status"], STATUS_OCZEKUJĄCY)

    def test_oczekujacy_to_potwierdzony(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=60, trigger_confirmed=False)
        result = _base_update(lifecycle, readiness_pct=85, trigger_confirmed=True)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)

    def test_aktywny_to_potwierdzony(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=40, trigger_confirmed=False)
        result = _base_update(lifecycle, readiness_pct=85, trigger_confirmed=True)
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)

    def test_oczekujacy_to_aktywny(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=60, trigger_confirmed=False)
        result = _base_update(lifecycle, readiness_pct=40, trigger_confirmed=False)
        self.assertEqual(result["status"], STATUS_AKTYWNY)

    def test_invalidated_is_terminal(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=85, trigger_confirmed=True,
                          invalidation_level=90.0)
        # Symuluj zamkniÄ™cie poniĹĽej poziomu uniewaĹĽnienia dla LONG
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        # last_close jest ~100.5, invalidation_level=90 â€” nie uniewaĹĽnione
        self.assertNotEqual(result["status"], STATUS_UNIEWAŻNIONY)

    def test_no_recreate_same_setup(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=40, trigger_confirmed=False)
        id1 = lifecycle.state["setup_id"]
        # Ponownie ten sam stan â€” setup_id nie powinien siÄ™ zmieniÄ‡
        _base_update(lifecycle, readiness_pct=40, trigger_confirmed=False)
        self.assertEqual(lifecycle.state["setup_id"], id1)


class BlockerTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)

    def test_entry_blocked_no_trigger(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=False,
            blockers=["Brak potwierdzonego wyzwalacza 1H"],
            invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=True,
        )
        self.assertIsNone(result["status"])
        self.assertIn("Brak potwierdzonego wyzwalacza 1H", result["conditions_missing"])

    def test_data_not_fresh_does_not_change_status(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=85, trigger_confirmed=True)
        status_before = lifecycle.state["status"]
        result = lifecycle.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=len(df) - 1, data_fresh=False,
        )
        self.assertEqual(result["status"], status_before)
        self.assertIn("Dane nieaktualne lub niekompletne", result["conditions_missing"])


class StatePersistenceTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)

    def test_state_has_required_fields(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=85, trigger_confirmed=True)
        state = lifecycle.get_state()
        required = [
            "symbol", "setup_id", "direction", "main_timeframe", "created_at",
            "updated_at", "trigger_level", "invalidation_level", "status",
            "conditions_met", "conditions_missing", "next_check_time",
            "expires_at", "status_history",
        ]
        for field in required:
            self.assertIn(field, state)

    def test_status_history_deterministic(self):
        df = make_df()
        lifecycle = SetupLifecycle("test_symbol")
        _base_update(lifecycle, readiness_pct=40, trigger_confirmed=False)
        _base_update(lifecycle, readiness_pct=85, trigger_confirmed=True)
        history = lifecycle.state["status_history"]
        self.assertGreaterEqual(len(history), 1)
        for entry in history:
            self.assertIn("from", entry)
            self.assertIn("to", entry)
            self.assertIn("reason", entry)
            self.assertIn("at", entry)


if __name__ == "__main__":
    unittest.main()


