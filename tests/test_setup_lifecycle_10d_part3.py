import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from analysis import setup_lifecycle
from analysis.setup_lifecycle import (
    SetupLifecycle,
    migrate_legacy_state,
    STATUS_AKTYWNY,
    STATUS_OCZEKUJĄCY,
    STATUS_POTWIERDZONY,
)
from config import SYMBOLS

SYMBOL_KEYS = list(SYMBOLS.keys())


def make_4h_df(bars=50, base=100.0):
    index = pd.date_range("2026-01-01", periods=bars, freq="4h", tz="UTC")
    close = pd.Series([base + i * 0.1 for i in range(bars)], index=index)
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.2,
        "low": close - 0.2, "close": close,
    }, index=index)


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_state(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "setup_id": "s1",
        "direction": "LONG",
        "main_timeframe": "4H",
        "created_at": "2026-01-01T10:00:00Z",
        "updated_at": "2026-01-01T10:00:00Z",
        "trigger_level": 100.0,
        "invalidation_level": 90.0,
        "status": STATUS_AKTYWNY,
        "conditions_met": [],
        "conditions_missing": [],
        "next_check_time": None,
        "expires_at": None,
        "last_setup_bar_index": 10,
        "setup_confirmed_at": None,
        "status_history": [{"from": None, "to": STATUS_AKTYWNY, "reason": "Nowy setup", "at": "2026-01-01T10:00:00Z"}],
    }


def _base_update(lifecycle, direction="LONG", readiness_pct=40,
                 trigger_confirmed=False, blockers=None, bar_index=40,
                 invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0):
    if blockers is None:
        blockers = []
    return lifecycle.update(
        direction=direction, readiness_pct=readiness_pct,
        trigger_confirmed=trigger_confirmed, blockers=blockers,
        invalidation_level=invalidation_level, entry=entry, stop=stop, target=target,
        df_4h=make_4h_df(bar_index + 1), current_bar_index=bar_index, data_fresh=True,
    )


class InstrumentIsolationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_isolation_two_instruments(self):
        """Zapis stanu jednego instrumentu nie zmienia stanu drugiego."""
        w20_path = self.tmp / "setup_state_w20.json"
        us500_path = self.tmp / "setup_state_us500.json"

        lc_w20 = SetupLifecycle("w20", state_path=w20_path)
        lc_us500 = SetupLifecycle("us500", state_path=us500_path)

        self.assertFalse(w20_path.exists())
        self.assertFalse(us500_path.exists())
        self.assertEqual(lc_w20.state["symbol"], "w20")
        self.assertEqual(lc_us500.state["symbol"], "us500")
        self.assertIsNone(lc_w20.state["status"])
        self.assertIsNone(lc_us500.state["status"])

        df = make_4h_df(45)
        result = lc_w20.update(
            direction="LONG", readiness_pct=85, trigger_confirmed=True,
            blockers=[], invalidation_level=90.0, entry=100.0, stop=95.0, target=110.0,
            df_4h=df, current_bar_index=40, data_fresh=True,
        )
        self.assertEqual(result["status"], STATUS_POTWIERDZONY)

        self.assertTrue(w20_path.exists())
        self.assertFalse(us500_path.exists())
        self.assertEqual(lc_us500.state["symbol"], "us500")
        self.assertIsNone(lc_us500.state["status"])
        self.assertIsNone(lc_us500.state["direction"])

        saved_w20 = json.loads(w20_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_w20["symbol"], "w20")
        self.assertEqual(saved_w20["status"], STATUS_POTWIERDZONY)

    def test_restart_restores_both_instrument_states(self):
        """Oba instrumenty odtwarzają własne stany po ponownym utworzeniu obiektów."""
        w20_path = self.tmp / "setup_state_w20.json"
        us500_path = self.tmp / "setup_state_us500.json"

        lc1 = SetupLifecycle("w20", state_path=w20_path)
        _base_update(lc1, readiness_pct=85, trigger_confirmed=True, bar_index=40)
        self.assertEqual(lc1.state["status"], STATUS_POTWIERDZONY)
        created_at_w20 = lc1.state["created_at"]

        lc2 = SetupLifecycle("us500", state_path=us500_path)
        _base_update(lc2, direction="SHORT", readiness_pct=60, trigger_confirmed=False, bar_index=40)
        self.assertEqual(lc2.state["status"], STATUS_OCZEKUJĄCY)
        self.assertEqual(lc2.state["direction"], "SHORT")

        lc1b = SetupLifecycle("w20", state_path=w20_path)
        lc2b = SetupLifecycle("us500", state_path=us500_path)
        self.assertEqual(lc1b.state["status"], STATUS_POTWIERDZONY)
        self.assertEqual(lc1b.state["created_at"], created_at_w20)
        self.assertEqual(lc2b.state["status"], STATUS_OCZEKUJĄCY)
        self.assertEqual(lc2b.state["direction"], "SHORT")

        self.assertEqual(json.loads(w20_path.read_text(encoding="utf-8"))["symbol"], "w20")
        self.assertEqual(json.loads(us500_path.read_text(encoding="utf-8"))["symbol"], "us500")


class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.src = self.tmp / "setup_state.json"
        self.out = self.tmp / "output"
        self.out.mkdir()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_migration_allowed_symbol(self):
        """Poprawna migracja legacy dla dozwolonego symbolu."""
        state = _base_state("w20")
        _write_json(self.src, state)
        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        target = self.out / "setup_state_w20.json"
        self.assertTrue(target.exists())
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), state)

        self.assertTrue(self.src.exists())
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8")), state)

    def test_migration_preserves_original_file(self):
        """Oryginalny setup_state.json nie jest usuwany ani nadpisywany."""
        state = _base_state("us500")
        _write_json(self.src, state)
        before = self.src.read_text(encoding="utf-8")

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        after = self.src.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertTrue(self.src.exists())

    def test_migration_idempotent(self):
        """Wielokrotne uruchomienie migracji nie nadpisuje ani nie niszczy danych."""
        state = _base_state("gold")
        _write_json(self.src, state)
        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        target = self.out / "setup_state_gold.json"
        first = target.read_text(encoding="utf-8")

        migrate_legacy_state(source_path=self.src, output_dir=self.out)
        second = target.read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8")), state)

    def test_migration_without_symbol(self):
        """Brak symbolu w legacy — brak migracji, plik źródłowy zachowany."""
        _write_json(self.src, {"status": STATUS_AKTYWNY})
        migrate_legacy_state(source_path=self.src, output_dir=self.out)
        self.assertFalse(list(self.out.glob("setup_state_*.json")))
        self.assertTrue(self.src.exists())

    def test_migration_invalid_json(self):
        """Nieprawidłowy JSON — brak migracji, plik źródłowy zachowany."""
        self.src.write_text("{niepoprawny json", encoding="utf-8")
        migrate_legacy_state(source_path=self.src, output_dir=self.out)
        self.assertFalse(list(self.out.glob("setup_state_*.json")))
        self.assertTrue(self.src.exists())

    def test_migration_unknown_symbol(self):
        """Symbol spoza dozwolonej listy — brak migracji, plik źródłowy zachowany."""
        state = _base_state("NIEZNANY_SYMBOL")
        _write_json(self.src, state)
        migrate_legacy_state(source_path=self.src, output_dir=self.out)
        self.assertFalse(list(self.out.glob("setup_state_*.json")))
        self.assertTrue(self.src.exists())

    def test_migration_conflict_existing_target(self):
        """Konflikt z istniejącym plikiem docelowym — oba pliki bez zmian."""
        legacy = _base_state("silver")
        legacy["setup_id"] = "legacy-1"
        _write_json(self.src, legacy)

        existing = _base_state("silver")
        existing["setup_id"] = "existing-1"
        _write_json(self.out / "setup_state_silver.json", existing)

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        self.assertEqual(
            json.loads((self.out / "setup_state_silver.json").read_text(encoding="utf-8"))["setup_id"],
            "existing-1",
        )
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8"))["setup_id"], "legacy-1")

    def test_migration_does_not_overwrite_existing_target(self):
        """Istniejący plik docelowy nie jest nadpisywany nawet przy ponownej migracji (double-check/TOCTOU)."""
        state = _base_state("silver")
        state["setup_id"] = "legacy-1"
        _write_json(self.src, state)

        existing = _base_state("silver")
        existing["setup_id"] = "existing-1"
        _write_json(self.out / "setup_state_silver.json", existing)

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        self.assertEqual(
            json.loads((self.out / "setup_state_silver.json").read_text(encoding="utf-8"))["setup_id"],
            "existing-1",
        )
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8"))["setup_id"], "legacy-1")

    def test_migration_atomic_create_no_overwrite(self):
        """Istniejący plik docelowy nie jest nadpisywany przez operację tworzenia celu (atomowe O_EXCL)."""
        legacy = _base_state("silver")
        legacy["setup_id"] = "legacy-1"
        _write_json(self.src, legacy)

        existing = _base_state("silver")
        existing["setup_id"] = "existing-1"
        existing_path = self.out / "setup_state_silver.json"
        _write_json(existing_path, existing)

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        # Plik docelowy musi zachować swoją oryginalną zawartość.
        self.assertEqual(
            json.loads(existing_path.read_text(encoding="utf-8"))["setup_id"],
            "existing-1",
        )
        # Plik źródłowy legacy nadal istnieje i nie został zmieniony.
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8"))["setup_id"], "legacy-1")
        # Nie pozostał żaden plik tymczasowy po operacji tworzącej.
        self.assertFalse((self.out / "setup_state_silver.json.tmp").exists())

    def test_migration_parallel_create_target_no_overwrite(self):
        """Równoległa próba utworzenia celu nie prowadzi do nadpisania esistącego pliku.

        Symuluje inny proces, który utworzył plik docelowy przed tą migracją.
        """
        legacy = _base_state("silver")
        legacy["setup_id"] = "legacy-1"
        _write_json(self.src, legacy)

        # Cel już istnieje (utworzony przez "równoległy" proces) z inną zawartością.
        existing = _base_state("silver")
        existing["setup_id"] = "parallel-1"
        target = self.out / "setup_state_silver.json"
        _write_json(target, existing)

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        # Cel nie został nadpisany — zachował zawartość równoległego procesu.
        self.assertEqual(
            json.loads(target.read_text(encoding="utf-8"))["setup_id"], "parallel-1"
        )
        # Plik źródłowy nienaruszony.
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8"))["setup_id"], "legacy-1")
        # Nie pozostały pliki tymczasowe.
        tmp_files = list(self.out.glob("setup_state_silver.*.tmp"))
        self.assertEqual(tmp_files, [])

    def test_migration_conflict_content_reported(self):
        """Konflikt zawartości jest zgłoszony (log WARNING), oba pliki bez zmian."""
        legacy = _base_state("silver")
        legacy["setup_id"] = "legacy-1"
        _write_json(self.src, legacy)

        existing = _base_state("silver")
        existing["setup_id"] = "existing-1"
        target = self.out / "setup_state_silver.json"
        _write_json(target, existing)

        with self.assertLogs(setup_lifecycle.logger, level="WARNING") as cm:
            migrate_legacy_state(source_path=self.src, output_dir=self.out)

        self.assertTrue(any("Konflikt migracji legacy" in msg for msg in cm.output))
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["setup_id"], "existing-1")
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8"))["setup_id"], "legacy-1")

    def test_migration_idempotent_existing_target_unchanged(self):
        """Zgodna zawartość istniejącego celu oznacza idempotencję — brak nadpisania."""
        state = _base_state("gold")
        _write_json(self.src, state)
        _write_json(self.out / "setup_state_gold.json", state)

        target = self.out / "setup_state_gold.json"
        before = target.read_text(encoding="utf-8")

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        self.assertEqual(target.read_text(encoding="utf-8"), before)
        self.assertTrue(self.src.exists())
        tmp_files = list(self.out.glob("setup_state_gold.*.tmp"))
        self.assertEqual(tmp_files, [])

    def test_migration_no_hardlink_support_aborts_safely(self):
        """Brak obsługi os.link() kończy się bezpiecznie — brak nadpisania, bez fallbacku."""
        state = _base_state("copper")
        _write_json(self.src, state)

        target = self.out / "setup_state_copper.json"

        with patch.object(setup_lifecycle.os, "link", side_effect=OSError("no hard link support")):
            with self.assertLogs(setup_lifecycle.logger, level="WARNING") as cm:
                migrate_legacy_state(source_path=self.src, output_dir=self.out)

        # Cel nie został utworzony ani nadpisany.
        self.assertFalse(target.exists())
        # Plik źródłowy nienaruszony.
        self.assertTrue(self.src.exists())
        self.assertEqual(json.loads(self.src.read_text(encoding="utf-8"))["symbol"], "copper")
        # Nie pozostały pliki tymczasowe.
        tmp_files = list(self.out.glob("setup_state_copper.*.tmp"))
        self.assertEqual(tmp_files, [])
        self.assertTrue(any("hard link" in msg for msg in cm.output))

    def test_migration_no_temp_files_remain_on_success(self):
        """Po udanej operacji nie pozostają pliki tymczasowe w katalogu docelowym."""
        state = _base_state("w20")
        _write_json(self.src, state)

        migrate_legacy_state(source_path=self.src, output_dir=self.out)

        target = self.out / "setup_state_w20.json"
        self.assertTrue(target.exists())
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["symbol"], "w20")
        # Żaden plik pasujący do wzorca tymczasowego nie został.
        tmp_files = list(self.out.glob("setup_state_w20.*.tmp"))
        self.assertEqual(tmp_files, [])


class LoadStateValidationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_missing_file_uses_empty_state_and_creates_nothing(self):
        path = self.tmp / "setup_state_eurusd.json"
        self.assertFalse(path.exists())

        lc = SetupLifecycle("eurusd", state_path=path)
        self.assertEqual(lc.state["symbol"], "eurusd")
        self.assertIsNone(lc.state["status"])
        self.assertFalse(path.exists())

    def test_corrupted_json_uses_empty_state_and_keeps_file(self):
        path = self.tmp / "setup_state_copper.json"
        path.write_text("to nie jest poprawny json", encoding="utf-8")

        lc = SetupLifecycle("copper", state_path=path)
        self.assertEqual(lc.state["symbol"], "copper")
        self.assertIsNone(lc.state["status"])
        self.assertTrue(path.exists())

    def test_load_state_rejects_foreign_symbol(self):
        """Plik ze symbolem innym niż self.symbol jest odrzucany, stan pusty dla bieżącego instrumentu."""
        path = self.tmp / "setup_state_us500.json"
        _write_json(path, _base_state("us500"))

        lc = SetupLifecycle("w20", state_path=path)
        self.assertEqual(lc.state["symbol"], "w20")
        self.assertIsNone(lc.state["status"])
        self.assertIsNone(lc.state["direction"])

        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["symbol"], "us500")


if __name__ == "__main__":
    unittest.main()