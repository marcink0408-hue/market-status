# analysis/chart_png.py
"""
Etap G: generowanie wykresu PNG do wiadomosci Telegram.
Zgodnie z instrukcja: "Wiadomosc zawieralaby rowniez wykres PNG".
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")  # bez GUI (GitHub Actions / headless)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

OUTPUT = Path(__file__).resolve().parents[1] / "output"
PNG_DIR = OUTPUT / "alerts_png"
PNG_DIR.mkdir(parents=True, exist_ok=True)


def _to_dt(ts) -> datetime:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def render_chart_png(symbol: str, candles: list, entry=None, stop=None, target=None,
                     title: str | None = None, max_bars: int = 120) -> Path:
    """
    Rysuje swiece (ostatnie max_bars) + linie Entry/Stop/Target.
    Zwraca sciezke do PNG.
    """
    if not candles:
        raise ValueError(f"Brak swiec dla {symbol}")

    candles = candles[-max_bars:]
    times = [_to_dt(c["time"]) for c in candles]
    o = [c["open"] for c in candles]
    h = [c["high"] for c in candles]
    l = [c["low"] for c in candles]
    cl = [c["close"] for c in candles]

    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=120)
    fig.patch.set_facecolor("#0b0f14")
    ax.set_facecolor("#0b0f14")

    # swiece
    for i, (t, oo, hh, ll, cc) in enumerate(zip(times, o, h, l, cl)):
        color = "#22c55e" if cc >= oo else "#ef4444"
        ax.plot([t, t], [ll, hh], color=color, linewidth=1)
        ax.add_patch(Rectangle(
            (mdates.date2num(t) - 0.03, min(oo, cc)),
            0.06, abs(cc - oo),
            facecolor=color, edgecolor=color, linewidth=0.5
        ))

    # linie Entry/Stop/Target
    lines = []
    if entry is not None:
        lines.append(("ENTRY", entry, "#3b82f6"))
    if stop is not None:
        lines.append(("STOP LOSS", stop, "#ef4444"))
    if target is not None:
        lines.append(("TAKE PROFIT", target, "#22c55e"))
    for label, price, color in lines:
        ax.axhline(price, color=color, linestyle="--", linewidth=1.4, alpha=0.9)
        ax.text(times[-1], price, f" {label} {price:.2f}",
                color=color, fontsize=8, va="center", ha="left")

    # osie
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.tick_params(colors="#8b9bb0", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#243041")
    ax.grid(color="#1e293b", linewidth=0.5)
    ax.set_title(title or f"{symbol.upper()} 4H", color="#e8eef6", fontsize=11)
    fig.autofmt_xdate(rotation=30)

    safe_sym = (symbol or "?").upper()
    png_path = PNG_DIR / f"{safe_sym}_alert.png"
    fig.savefig(png_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return png_path