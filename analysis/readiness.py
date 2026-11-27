# analysis/readiness.py — model gotowości setupu (deterministyczny, brak uczenia)
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import (
    INVALIDATION_BUFFER_ATR_MULT,
    MAX_DATA_AGE,
    MIN_DIFFERENCE_POINTS,
    MIN_RR,
    READINESS_THRESHOLD_ENTRY_CANDIDATE,
    READINESS_THRESHOLD_NO_DIRECTION,
    READINESS_THRESHOLD_OBSERVE,
    READINESS_THRESHOLD_PREPARATION,
    READINESS_WEIGHTS,
    SETUP_EXPIRY_BARS,
    CONFIRMED_VALID_BARS,
)


def _num(value) -> float | None:
    try:
        v = float(value)
        if v != v or abs(v) == float("inf"):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _atr_value(atr) -> float | None:
    a = _num(atr)
    return a if (a is not None and a > 0) else None


def _stage_from_readiness(pct: int | None) -> str:
    if pct is None:
        return "BRAK DANYCH"
    if pct <= READINESS_THRESHOLD_NO_DIRECTION:
        return "BRAK KIERUNKU"
    if pct <= READINESS_THRESHOLD_OBSERVE:
        return "OBSERWUJ"
    if pct <= READINESS_THRESHOLD_PREPARATION:
        return "PRZYGOTOWANIE"
    return "KANDYDAT DO WEJŚCIA"


def score_context_1d(bias: str | None, side: str) -> int:
    if bias is None or bias == "BRAK":
        return 0
    if bias == side:
        return READINESS_WEIGHTS["context_1d"]
    if bias == "neutral":
        return 10
    return 0


def score_structure_4h(renko_aligned: bool, harmonic_active: bool, direction_match: bool) -> int:
    if not direction_match:
        return 0
    matches = sum([bool(renko_aligned), bool(harmonic_active)])
    if matches >= 2:
        return READINESS_WEIGHTS["structure_4h"]
    if matches == 1:
        return 12
    return 0


def score_sr_position(
    price_in_zone: bool,
    zone_distance_atr: float | None,
    side: str,
    zone_type: str | None,
    current_price: float | None,
    atr: float | None,
) -> int:
    atr = _atr_value(atr)
    if price_in_zone and zone_type:
        expected_zone = "SUPPORT" if side == "LONG" else "RESISTANCE"
        if zone_type == expected_zone:
            return READINESS_WEIGHTS["sr_position"]
        return 0
    if zone_distance_atr is not None and atr and atr > 0:
        if zone_distance_atr <= 0.5:
            return 10
    return 0


def score_trigger(confirmed: bool) -> int:
    return READINESS_WEIGHTS["trigger"] if confirmed else 0


def score_rr(rr_value: float | None) -> int:
    rr = _num(rr_value)
    if rr is None:
        return 0
    return READINESS_WEIGHTS["rr"] if rr >= MIN_RR else 0


def evaluate_side(
    side: str,
    context_1d: dict | None,
    structure_4h: dict | None,
    sr_position: dict | None,
    trigger: dict | None,
    rr_data: dict | None,
    current_price: float | None,
    atr: float | None,
) -> dict:
    ctx = context_1d or {}
    struct = structure_4h or {}
    sr = sr_position or {}
    trg = trigger or {}
    rr = rr_data or {}

    c_pts = score_context_1d(ctx.get("bias"), side)
    s_pts = score_structure_4h(
        struct.get("renko_aligned", False),
        struct.get("harmonic_active", False),
        struct.get("direction_match", False),
    )
    sr_pts = score_sr_position(
        sr.get("price_in_zone", False),
        sr.get("zone_distance_atr"),
        side,
        sr.get("zone_type"),
        current_price,
        atr,
    )
    t_pts = score_trigger(trg.get("confirmed", False))
    r_pts = score_rr(rr.get("rr"))

    criteria = [
        {
            "id": "context_1d",
            "name": "Kontekst 1D",
            "points": c_pts,
            "max": READINESS_WEIGHTS["context_1d"],
            "met": c_pts == READINESS_WEIGHTS["context_1d"],
            "note": ctx.get("note", ""),
        },
        {
            "id": "structure_4h",
            "name": "Struktura 4H",
            "points": s_pts,
            "max": READINESS_WEIGHTS["structure_4h"],
            "met": s_pts == READINESS_WEIGHTS["structure_4h"],
            "note": struct.get("note", ""),
        },
        {
            "id": "sr_position",
            "name": "Położenie względem S/R",
            "points": sr_pts,
            "max": READINESS_WEIGHTS["sr_position"],
            "met": sr_pts == READINESS_WEIGHTS["sr_position"],
            "note": sr.get("note", ""),
        },
        {
            "id": "trigger",
            "name": "Wyzwalacz 1H",
            "points": t_pts,
            "max": READINESS_WEIGHTS["trigger"],
            "met": t_pts == READINESS_WEIGHTS["trigger"],
            "note": trg.get("note", ""),
        },
        {
            "id": "rr",
            "name": "Stosunek zysk/ryzyko (R:R)",
            "points": r_pts,
            "max": READINESS_WEIGHTS["rr"],
            "met": r_pts == READINESS_WEIGHTS["rr"],
            "note": rr.get("note", ""),
        },
    ]

    total = sum(c["points"] for c in criteria)

    missing = []
    for c in criteria:
        if c["points"] < c["max"]:
            missing.append(c["name"])
    missing.sort(key=lambda m: next(
        (c["max"] - c["points"]) for c in criteria if c["name"] == m
    ), reverse=True)

    return {
        "side": side,
        "readiness_pct": int(total),
        "criteria": criteria,
        "missing": missing,
        "trigger_level": trg.get("trigger_level"),
        "invalidation_level": rr.get("invalidation_level"),
        "entry": rr.get("entry"),
        "stop": rr.get("stop"),
        "target": rr.get("target"),
        "rr": rr.get("rr"),
    }


def _check_blockers(
    side_eval: dict,
    data_fresh: bool,
    invalidated: bool,
    expired: bool,
    entry_valid: bool,
    sl_valid: bool,
    tp_valid: bool,
) -> list[str]:
    blockers: list[str] = []
    if not side_eval["criteria"][3]["met"]:
        blockers.append("Brak potwierdzonego wyzwalacza 1H")
    rr_val = side_eval["rr"]
    if rr_val is None or rr_val < MIN_RR:
        blockers.append("RR poniżej 1.5 lub nieznane")
    if not data_fresh:
        blockers.append("Dane nieaktualne lub niekompletne")
    if invalidated:
        blockers.append("Scenariusz unieważniony")
    if expired:
        blockers.append("Setup wygasł")
    if not entry_valid:
        blockers.append("Nieprawidłowy poziom Entry")
    if not sl_valid:
        blockers.append("Nieprawidłowy poziom SL")
    if not tp_valid:
        blockers.append("Nieprawidłowy poziom TP")
    invalid_lvl = side_eval["invalidation_level"]
    entry_lvl = side_eval["entry"]
    if invalid_lvl is None:
        blockers.append("Brak poprawnego poziomu unieważnienia")
    elif entry_lvl is not None:
        if side_eval["side"] == "LONG" and not (invalid_lvl < entry_lvl):
            blockers.append("Poziom unieważnienia nieprawidłowy dla LONG")
        if side_eval["side"] == "SHORT" and not (invalid_lvl > entry_lvl):
            blockers.append("Poziom unieważnienia nieprawidłowy dla SHORT")
    return blockers


def _validate_levels(side: str, entry, stop, target) -> tuple[bool, bool, bool]:
    e = _num(entry)
    s = _num(stop)
    t = _num(target)
    entry_valid = e is not None and e > 0
    sl_valid = False
    tp_valid = False
    if e is not None and s is not None:
        if side == "LONG":
            sl_valid = s < e and (e - s) > 0
        else:
            sl_valid = s > e and (s - e) > 0
    if e is not None and t is not None and s is not None:
        if side == "LONG":
            tp_valid = t > e and (t - e) > 0
        else:
            tp_valid = t < e and (e - t) > 0
        if tp_valid and sl_valid:
            risk = abs(e - s)
            reward = abs(t - e)
            tp_valid = risk > 0 and (reward / risk) > 0
    return entry_valid, sl_valid, tp_valid


def calculate_readiness(
    symbol: str,
    main_timeframe: str,
    long_data: dict | None,
    short_data: dict | None,
    current_price: float | None,
    atr: float | None,
    data_fresh: bool,
    long_invalidated: bool,
    short_invalidated: bool,
    long_expired: bool,
    short_expired: bool,
    next_check_time: str | None = None,
    expires_at: str | None = None,
    data_as_of: str | None = None,
    generated_at: str | None = None,
) -> dict:
    cp = _num(current_price)
    a = _atr_value(atr)

    long_eval = evaluate_side(
        "LONG",
        (long_data or {}).get("context_1d"),
        (long_data or {}).get("structure_4h"),
        (long_data or {}).get("sr_position"),
        (long_data or {}).get("trigger"),
        (long_data or {}).get("rr"),
        cp, a,
    )
    short_eval = evaluate_side(
        "SHORT",
        (short_data or {}).get("context_1d"),
        (short_data or {}).get("structure_4h"),
        (short_data or {}).get("sr_position"),
        (short_data or {}).get("trigger"),
        (short_data or {}).get("rr"),
        cp, a,
    )

    long_entry_valid, long_sl_valid, long_tp_valid = _validate_levels(
        "LONG", long_eval["entry"], long_eval["stop"], long_eval["target"]
    )
    short_entry_valid, short_sl_valid, short_tp_valid = _validate_levels(
        "SHORT", short_eval["entry"], short_eval["stop"], short_eval["target"]
    )

    long_blockers = _check_blockers(
        long_eval, data_fresh, long_invalidated, long_expired,
        long_entry_valid, long_sl_valid, long_tp_valid,
    )
    short_blockers = _check_blockers(
        short_eval, data_fresh, short_invalidated, short_expired,
        short_entry_valid, short_sl_valid, short_tp_valid,
    )

    long_readiness = long_eval["readiness_pct"]
    short_readiness = short_eval["readiness_pct"]

    long_allowed = (
        long_readiness >= READINESS_THRESHOLD_ENTRY_CANDIDATE
        and not long_blockers
    )
    short_allowed = (
        short_readiness >= READINESS_THRESHOLD_ENTRY_CANDIDATE
        and not short_blockers
    )

    direction = "NONE"
    if long_allowed and not short_allowed:
        direction = "LONG"
    elif short_allowed and not long_allowed:
        direction = "SHORT"
    elif long_allowed and short_allowed:
        diff = abs(long_readiness - short_readiness)
        if diff >= MIN_DIFFERENCE_POINTS:
            direction = "LONG" if long_readiness > short_readiness else "SHORT"
        else:
            direction = "NONE"
    else:
        direction = "NONE"

    stage = _stage_from_readiness(
        long_readiness if direction == "LONG" else
        short_readiness if direction == "SHORT" else
        max(long_readiness, short_readiness)
    )

    entry_allowed = direction in ("LONG", "SHORT") and (
        (long_allowed if direction == "LONG" else short_allowed)
    )

    selected = long_eval if direction == "LONG" else short_eval if direction == "SHORT" else None

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "symbol": symbol,
        "main_timeframe": main_timeframe,
        "direction": direction,
        "readiness_pct": (
            selected["readiness_pct"] if selected else max(long_readiness, short_readiness)
        ),
        "stage": stage,
        "setup_status": "AKTYWNY" if direction != "NONE" and long_readiness >= 30 else "BRAK SETUPU",
        "entry_allowed": bool(entry_allowed),
        "blockers": list(dict.fromkeys(
            (selected["missing"] if selected else [])
            + (long_blockers if direction == "LONG" else short_blockers if direction == "SHORT" else [])
            + (long_blockers + short_blockers if direction == "NONE" else [])
        )),
        "criteria": (selected["criteria"] if selected else []),
        "scores": {
            "LONG": {"readiness_pct": long_readiness, "blockers": long_blockers},
            "SHORT": {"readiness_pct": short_readiness, "blockers": short_blockers},
        },
        "missing": (selected["missing"] if selected else []),
        "trigger_level": selected["trigger_level"] if selected else None,
        "invalidation_level": selected["invalidation_level"] if selected else None,
        "entry": selected["entry"] if selected else None,
        "stop": selected["stop"] if selected else None,
        "target": selected["target"] if selected else None,
        "rr": selected["rr"] if selected else None,
        "next_check_time": next_check_time,
        "expires_at": expires_at,
        "data_as_of": data_as_of,
        "generated_at": generated_at or now_utc,
    }


def readiness_stage_label(pct: int | None) -> str:
    return _stage_from_readiness(pct)


def is_entry_allowed(readiness_pct: int | None, blockers: list | None) -> bool:
    if readiness_pct is None:
        return False
    if readiness_pct < READINESS_THRESHOLD_ENTRY_CANDIDATE:
        return False
    if blockers:
        return False
    return True