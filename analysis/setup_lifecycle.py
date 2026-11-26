# analysis/setup_lifecycle.py — moduł zarządzania cyklem życia setupu
from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import CONFIRMED_VALID_BARS, SETUP_EXPIRY_BARS

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
STATE_PATH = OUTPUT_DIR / "setup_state.json"

# Dopuszczalne statusy setupu
STATUS_AKTYWNY = "AKTYWNY"
STATUS_OCZEKUJĄCY = "OCZEKUJĄCY"
STATUS_POTWIERDZONY = "POTWIERDZONY"
STATUS_UNIEWAŻNIONY = "UNIEWAŻNIONY"
STATUS_WYGASŁY = "WYGASŁY"

# Statusy terminalne
TERMINAL_STATUSES = {STATUS_UNIEWAŻNIONY, STATUS_WYGASŁY}

# Pierwsieństwo statusów (wyższa wartość = wyższe pierwszeństwo)
STATUS_PRIORITY = {
    STATUS_UNIEWAŻNIONY: 5,
    STATUS_WYGASŁY: 4,
    STATUS_POTWIERDZONY: 3,
    STATUS_OCZEKUJĄCY: 2,
    STATUS_AKTYWNY: 1,
}

# Mapowanie gotowości na status (przy braku blokad terminalnych)
READINESS_TO_STATUS = {
    (30, 54): STATUS_AKTYWNY,
    (55, 79): STATUS_OCZEKUJĄCY,
    (80, 100): STATUS_POTWIERDZONY,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None


def _priority(status: str) -> int:
    return STATUS_PRIORITY.get(status, 0)


def _status_from_readiness(readiness_pct: int | None) -> str | None:
    """Mapuje gotowość na status przy braku blokad terminalnych."""
    if readiness_pct is None:
        return None
    if readiness_pct < 30:
        return None
    if readiness_pct <= 54:
        return STATUS_AKTYWNY
    if readiness_pct <= 79:
        return STATUS_OCZEKUJĄCY
    if readiness_pct >= 80:
        return STATUS_POTWIERDZONY
    return None


def _count_session_bars(df, from_index: int, to_index: int, timeframe: str) -> int:
    """Liczy rzeczywiste świece sesyjne (4H) między indeksami, pomijając weekendy i przerwy."""
    if df is None or df.empty:
        return 0
    count = 0
    for i in range(from_index + 1, min(to_index + 1, len(df))):
        stamp = df.index[i]
        try:
            ts = stamp.tz_convert("UTC") if stamp.tzinfo else stamp.tz_localize("UTC")
        except Exception:
            continue
        # Pomijamy weekendy (sobota=5, niedziela=6)
        if ts.weekday() >= 5:
            continue
        count += 1
    return count


class SetupLifecycle:
    """Zarządza cyklem życia setupu między uruchomieniami silnika."""

    def __init__(self, symbol: str, state_path: Path = STATE_PATH):
        self.symbol = symbol
        self.state_path = state_path
        self.state: dict[str, Any] = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Wczytuje stan z pliku. Uszkodzony plik nie powoduje awarii."""
        if not self.state_path.exists():
            return self._empty_state()
        try:
            raw = self.state_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return self._empty_state()
            # Bezpieczna migracja — zachowaj poprawne pola
            return self._migrate_state(data)
        except (json.JSONDecodeError, OSError, ValueError):
            # Uszkodzony plik — nie zastępuj fikcyjnymi danymi, zwróć pusty stan
            return self._empty_state()

    def _empty_state(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "setup_id": None,
            "direction": None,
            "main_timeframe": None,
            "created_at": None,
            "updated_at": None,
            "trigger_level": None,
            "invalidation_level": None,
            "status": None,
            "conditions_met": [],
            "conditions_missing": [],
            "next_check_time": None,
            "expires_at": None,
            "last_setup_bar_index": -1,
            "setup_confirmed_at": None,
            "status_history": [],
        }

    def _migrate_state(self, data: dict[str, Any]) -> dict[str, Any]:
        """Bezpieczna migracja istniejącego stanu — zachowaj poprawne pola."""
        state = self._empty_state()
        for key in state:
            if key in data:
                state[key] = data[key]
        return state

    def _save_state(self) -> None:
        """Zapisuje stan odpornie na przerwanie procesu (zapis atomowy)."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state["updated_at"] = _now_iso()
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    def _new_setup_id(self) -> str:
        return f"{self.symbol}_{_now_iso()}"

    def _append_history(self, from_status: str | None, to_status: str, reason: str) -> None:
        self.state.setdefault("status_history", []).append({
            "from": from_status,
            "to": to_status,
            "reason": reason,
            "at": _now_iso(),
        })

    def _set_status(self, new_status: str, reason: str, at_iso: str | None = None) -> None:
        old_status = self.state.get("status")
        if old_status == new_status:
            return
        self.state["status"] = new_status
        if new_status == STATUS_POTWIERDZONY:
            self.state["setup_confirmed_at"] = at_iso or _now_iso()
        self._append_history(old_status, new_status, reason)
        self._save_state()

    def update(
        self,
        direction: str | None,
        readiness_pct: int | None,
        trigger_confirmed: bool,
        blockers: list[str],
        invalidation_level: float | None,
        entry: float | None,
        stop: float | None,
        target: float | None,
        df_4h,
        current_bar_index: int,
        next_check_time: str | None = None,
        data_fresh: bool = True,
    ) -> dict[str, Any]:
        current_status = self.state.get("status")

        if not data_fresh:
            self.state["direction"] = direction
            self.state["conditions_met"] = []
            self.state["conditions_missing"] = ["Dane nieaktualne lub niekompletne"]
            self.state["next_check_time"] = next_check_time
            self._save_state()
            return self.get_state()

        # Ostatnia rzeczywiście zamknięta świeca 4H (nie automatycznie ostatni wiersz).
        closed_bar_index = self._last_closed_bar_index(df_4h, current_bar_index)

        if closed_bar_index is None:
            # Brak wiarygodnego indeksu zamkniętej świecy 4H — nie podejmuj działań
            # zależnych od nowej zamkniętej świecy. Zachowaj istniejący stan setupu bez zmian.
            return self.get_state()

        invalidation_triggered = self._check_invalidation(df_4h, closed_bar_index, direction)
        if invalidation_triggered:
            self.state["last_setup_bar_index"] = closed_bar_index
            self._set_status(STATUS_UNIEWAŻNIONY, invalidation_triggered)
            self.state["direction"] = None
            self.state["conditions_met"] = []
            self.state["conditions_missing"] = [invalidation_triggered]
            self._save_state()
            return self.get_state()

        expiry_reason = self._check_expiry(df_4h, closed_bar_index, current_status)
        if expiry_reason:
            self.state["last_setup_bar_index"] = closed_bar_index
            self._set_status(STATUS_WYGASŁY, expiry_reason)
            self.state["direction"] = None
            self.state["conditions_met"] = []
            self.state["conditions_missing"] = [expiry_reason]
            self._save_state()
            return self.get_state()

        has_terminal_blocker = any(
            b in blockers for b in [
                "Brak potwierdzonego wyzwalacza 1H",
                "RR poniżej 1.5 lub nieznane",
                "Nieprawidłowy poziom Entry",
                "Nieprawidłowy poziom SL",
                "Nieprawidłowy poziom TP",
                "Brak poprawnego poziomu unieważnienia",
                "Poziom unieważnienia nieprawidłowy dla LONG",
                "Poziom unieważnienia nieprawidłowy dla SHORT",
            ]
        )

        if readiness_pct is None or readiness_pct < 30:
            if current_status not in TERMINAL_STATUSES:
                self._set_status(None, "Gotowość poniżej 30 — brak aktywnego setupu")
            self.state["direction"] = None
            self.state["conditions_met"] = []
            self.state["conditions_missing"] = ["Gotowość poniżej 30"]
            self.state["next_check_time"] = next_check_time
            self._save_state()
            return self.get_state()

        target_status = _status_from_readiness(readiness_pct)

        # Zasada: nowy setup może powstać najwcześniej na następnej zamkniętej świecy 4H
        # po zakończeniu poprzedniego setupu.
        next_bar_allowed = self.state.get("last_setup_bar_index", -1) + 1

        if current_status in TERMINAL_STATUSES:
            if (direction and readiness_pct >= 30 and not has_terminal_blocker
                    and closed_bar_index >= next_bar_allowed):
                self._create_new_setup(direction, readiness_pct, trigger_confirmed,
                                       invalidation_level, entry, stop, target,
                                       df_4h, closed_bar_index, next_check_time)
            self.state["conditions_missing"] = blockers
            self._save_state()
            return self.get_state()

        if current_status is None:
            if direction and readiness_pct >= 30 and not has_terminal_blocker and closed_bar_index >= next_bar_allowed:
                if readiness_pct >= 80 and trigger_confirmed:
                    # Gotowość >= 80 z potwierdzonym wyzwalaczem → od razu POTWIERDZONY
                    new_status = STATUS_POTWIERDZONY
                elif readiness_pct >= 55:
                    new_status = STATUS_OCZEKUJĄCY
                else:
                    new_status = STATUS_AKTYWNY
                self._create_new_setup(direction, readiness_pct, trigger_confirmed,
                                       invalidation_level, entry, stop, target,
                                       df_4h, closed_bar_index, next_check_time,
                                       new_status)
            self.state["conditions_missing"] = blockers
            self._save_state()
            return self.get_state()

        # Znacznik czasu ostatniej zamkniętej świecy 4H (dla trwałego zapisu potwierdzenia).
        current_candle_iso = None
        try:
            cc = df_4h.index[closed_bar_index]
            if hasattr(cc, "tz_convert"):
                cc = cc.tz_convert("UTC")
            elif hasattr(cc, "tz_localize"):
                cc = cc.tz_localize("UTC")
            current_candle_iso = cc.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            current_candle_iso = None

        if current_status == STATUS_AKTYWNY:
            if readiness_pct >= 55 and (not trigger_confirmed or has_terminal_blocker):
                self._set_status(STATUS_OCZEKUJĄCY, "Gotowość >= 55, brak potwierdzonego wyzwalacza lub blokada")
            elif readiness_pct >= 80 and trigger_confirmed and not has_terminal_blocker:
                self._set_status(STATUS_POTWIERDZONY, "Gotowość >= 80, wyzwalacz potwierdzony, brak blokady", current_candle_iso)
            self.state["conditions_missing"] = blockers
            self._save_state()
            return self.get_state()

        if current_status == STATUS_OCZEKUJĄCY:
            if readiness_pct >= 80 and trigger_confirmed and not has_terminal_blocker:
                self._set_status(STATUS_POTWIERDZONY, "Gotowość >= 80, wyzwalacz potwierdzony, brak blokady", current_candle_iso)
            elif 30 <= readiness_pct <= 54:
                self._set_status(STATUS_AKTYWNY, "Gotowość spadła poniżej 55")
            self.state["conditions_missing"] = blockers
            self._save_state()
            return self.get_state()

        if current_status == STATUS_POTWIERDZONY:
            self.state["conditions_missing"] = blockers
            self._save_state()
            return self.get_state()

        self.state["conditions_missing"] = blockers
        self._save_state()
        return self.get_state()

    def _create_new_setup(
        self,
        direction: str,
        readiness_pct: int | None,
        trigger_confirmed: bool,
        invalidation_level: float | None,
        entry: float | None,
        stop: float | None,
        target: float | None,
        df_4h,
        current_bar_index: int,
        next_check_time: str | None,
        new_status: str | None = None,
    ) -> None:
        setup_id = self._new_setup_id()
        now_iso = _now_iso()
        if new_status is not None:
            status = new_status
        elif readiness_pct is not None and readiness_pct >= 80 and trigger_confirmed:
            status = STATUS_POTWIERDZONY
        else:
            status = STATUS_AKTYWNY if 30 <= (readiness_pct or 0) <= 54 else STATUS_OCZEKUJĄCY

        # Liczba świec do wygaśnięcia dla tego statusu.
        bars_needed = CONFIRMED_VALID_BARS if status == STATUS_POTWIERDZONY else SETUP_EXPIRY_BARS

        # Znacznik czasu świecy na której utworzono setup (nie czas zegara).
        created_candle_iso = None
        try:
            cb = df_4h.index[current_bar_index]
            if hasattr(cb, "tz_convert"):
                cb = cb.tz_convert("UTC")
            elif hasattr(cb, "tz_localize"):
                cb = cb.tz_localize("UTC")
            created_candle_iso = cb.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            created_candle_iso = now_iso

        # expires_at tylko dla kompatybilności wstecznej — nie używane w logice wygasania.
        expires_at = None
        try:
            target_idx = current_bar_index + bars_needed
            if df_4h is not None and not df_4h.empty:
                idx = min(target_idx, len(df_4h) - 1)
                tb = df_4h.index[idx]
                if hasattr(tb, "tz_convert"):
                    tb = tb.tz_convert("UTC")
                elif hasattr(tb, "tz_localize"):
                    tb = tb.tz_localize("UTC")
                expires_at = tb.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            expires_at = None

        self.state = {
            "symbol": self.symbol,
            "setup_id": setup_id,
            "direction": direction,
            "main_timeframe": "4H",
            "created_at": created_candle_iso,
            "updated_at": now_iso,
            "trigger_level": entry,
            "invalidation_level": invalidation_level,
            "status": status,
            "conditions_met": [] if trigger_confirmed else ["Brak potwierdzonego wyzwalacza 1H"],
            "conditions_missing": [] if trigger_confirmed else ["Brak potwierdzonego wyzwalacza 1H"],
            "next_check_time": next_check_time,
            "expires_at": expires_at,
            "last_setup_bar_index": current_bar_index,
            "setup_confirmed_at": created_candle_iso if status == STATUS_POTWIERDZONY else None,
            "status_history": [{"from": None, "to": status, "reason": "Nowy setup", "at": now_iso}],
        }
        self._save_state()

    def _check_invalidation(self, df_4h, current_bar_index: int, direction: str | None) -> str | None:
        if direction is None or self.state.get("invalidation_level") is None:
            return None
        invalidation_level = float(self.state["invalidation_level"])
        if df_4h is None or df_4h.empty:
            return None
        last_close = float(df_4h["close"].iloc[-1])
        if direction == "LONG" and last_close < invalidation_level:
            return "Zamknięcie świecy 1H poniżej poziomu unieważnienia"
        if direction == "SHORT" and last_close > invalidation_level:
            return "Zamknięcie świecy 1H powyżej poziomu unieważnienia"
        return None

    def _last_closed_bar_index(self, df_4h, current_bar_index: int) -> int | None:
        """Zwraca indeks ostatniej rzeczywiście zamkniętej świecy 4H.

        Zwraca None gdy nie można wiarygodnie określić zamkniętej świecy
        (brak danych, tz-naive, błąd konwersji, brak poprzedniej świecy).
        Nie zwraca current_bar_index jako fallback ani indeksu -1.
        """
        if df_4h is None or df_4h.empty or current_bar_index < 0:
            return None
        try:
            last_ts = df_4h.index[current_bar_index]
            # Jawnie sprawdź czy timestamp ma określoną strefę czasową.
            # Timestamp tz-naive nie może być automatycznie traktowany jako UTC.
            tzinfo = getattr(last_ts, "tzinfo", None)
            if tzinfo is None:
                return None
            try:
                last_ts = last_ts.tz_convert("UTC")
            except Exception:
                return None
            now_utc = datetime.now(timezone.utc)
            # Świeca 4H otwierająca się o last_ts jest zamknięta jeśli
            # last_ts + 4h <= teraz. W przeciwnym razie jest nadal tworzona.
            if last_ts + timedelta(hours=4) > now_utc:
                prev_index = current_bar_index - 1
                if prev_index < 0:
                    return None
                return prev_index
            return current_bar_index
        except Exception:
            return None

    def _count_bars_after(self, df_4h, reference_iso: str | None, current_bar_index: int | None = None) -> int | None:
        """Licz rzeczywiste zamknięte świece 4H po podanym znaczniku czasu.

        Zwraca liczbę świec w df_4h z indeksem czasowym większym niż reference_iso,
        licząc wyłącznie świece do pozycji current_bar_index (brak lookahead).
        Zwraca None jeśli nie można wiarygodnie ustalić liczby.
        """
        if df_4h is None or df_4h.empty or reference_iso is None:
            return None
        try:
            ref_dt = datetime.fromisoformat(reference_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        # Ogranicz do danych dostępnych do current_bar_index (brak lookahead w przyszłe dane)
        if current_bar_index is not None:
            df_4h = df_4h.iloc[:current_bar_index + 1]
        count = 0
        for stamp in df_4h.index:
            try:
                ts = stamp.tz_convert("UTC") if stamp.tzinfo else stamp.tz_localize("UTC")
            except Exception:
                continue
            if ts > ref_dt:
                count += 1
        return count

    def _check_expiry(self, df_4h, current_bar_index: int, current_status: str | None) -> str | None:
        if current_status in TERMINAL_STATUSES:
            return None
        if current_status not in (STATUS_AKTYWNY, STATUS_OCZEKUJĄCY, STATUS_POTWIERDZONY):
            return None
        if df_4h is None or df_4h.empty:
            return None

        if current_status == STATUS_POTWIERDZONY:
            reference = self.state.get("setup_confirmed_at")
            required = CONFIRMED_VALID_BARS
        else:
            reference = self.state.get("created_at")
            required = SETUP_EXPIRY_BARS

        if reference is None:
            return None

        bars_after = self._count_bars_after(df_4h, reference, current_bar_index)
        if bars_after is None:
            return None
        if bars_after >= required:
            if current_status == STATUS_POTWIERDZONY:
                return "Setup potwierdzony wygasł po CONFIRMED_VALID_BARS świecach"
            else:
                return "Setup niepotwierdzony wygasł po SETUP_EXPIRY_BARS świecach"
        return None

    def get_state(self) -> dict[str, Any]:
        return dict(self.state)

    def is_terminal(self) -> bool:
        return self.state.get("status") in TERMINAL_STATUSES

    def is_active_setup(self) -> bool:
        return self.state.get("status") in {STATUS_AKTYWNY, STATUS_OCZEKUJĄCY, STATUS_POTWIERDZONY}


def manage_lifecycle(
    symbol: str,
    direction: str | None,
    readiness_pct: int | None,
    trigger_confirmed: bool,
    blockers: list[str],
    invalidation_level: float | None,
    entry: float | None,
    stop: float | None,
    target: float | None,
    df_4h,
    current_bar_index: int,
    next_check_time: str | None = None,
    data_fresh: bool = True,
    state_path: Path = STATE_PATH,
) -> dict[str, Any]:
    lifecycle = SetupLifecycle(symbol, state_path)
    return lifecycle.update(
        direction, readiness_pct, trigger_confirmed, blockers,
        invalidation_level, entry, stop, target,
        df_4h, current_bar_index, next_check_time, data_fresh,
    )