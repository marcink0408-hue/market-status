# docs/PROJECT.md — Rzeczywisty stan projektu Market Status

## Struktura repozytorium

```
market-status/
├── app.py                      # Aplikacja Streamlit (desktopowa)
├── config.py                   # Konfiguracja symboli, interwałów, parametrów
├── run_daily.py                # Skrypt codziennej analizy (generuje dane JSON)
├── Kalkulator_XTB.html         # Kalkulator XTB (HTML)
├── requirements.txt            # Zależności Python
├── .gitignore                  # Git ignoruje __pycache__ i output/status_previous.json
├── .streamlit/
│   └── config.toml             # Konfiguracja wyglądu Streamlit
├── .github/
│   └── workflows/
│       ├── daily.yml           # Codzienne generowanie danych (cron)
│       └── commit_log.yml      # Ręczne wyzwalanie analizy + artefakty
├── analysis/                   # Silnik analityczny Python
│   ├── __init__.py
│   ├── alerts.py
│   ├── analyzer.py
│   ├── backtest.py
│   ├── candles.py
│   ├── chart_data.py
│   ├── chart_png.py
│   ├── classic_patterns.py
│   ├── decision.py
│   ├── decision_log.py
│   ├── harmonics.py
│   ├── renko.py
│   └── signal_history.py
├── data/
│   ├── __init__.py
│   └── fetcher.py              # Pobieranie danych rynkowych (yfinance)
├── frontend/
│   └── index.html              # Obecna aplikacja HTML z Lightweight Charts
└── output/                     # Dane wygenerowane przez run_daily.py (JSON)
    ├── backtest_results.json
    ├── classic_patterns.json
    ├── decisions_log.json
    ├── ohlc.json
    ├── ohlc_history.json
    ├── signals_history.json
    └── status.json
```

## Rola Pythona jako silnika analitycznego

Python (`run_daily.py` + moduły w `analysis/`) odpowiada za:
- Pobieranie danych rynkowych przez `yfinance`
- Wykrywanie formacji harmonicznych (XABCD: Gartley, Bat, Crab, Deep Crab, Butterfly)
- Wykrywanie formacji świecowych (np. Bullish/Bearish Engulfing, Hammer, Doji)
- Wykrywanie formacji klasycznych (np. Podwójny szczyt, Podwójne dno, Głowa z ramionami)
- Obliczanie decyzji handlowych (LONG / SHORT / BRAK) z poziomami entry, stop, target
- Obliczanie oceny sygnału (confidence 0–100)
- Prowadzenie dziennika decyzji (`decisions_log.json`)
- Prowadzenie historii sygnałów (`signals_history.json`)
- Wykrywanie formacji klasycznych (`classic_patterns.json`)
- Generowanie danych wykresów OHLC (`ohlc.json`, `ohlc_history.json`)

- Sprawdzanie alertów (Telegram)

Wyniki są zapisywane w katalogu `output/` jako pliki JSON.

## Rola GitHub Actions

Dwa pliki w `.github/workflows/`:
- `daily.yml` — uruchamiane codziennie o 6:00 UTC, uruchamia `run_daily.py`, commituje zaktualizowane pliki `output/*.json`
- `commit_log.yml` — uruchamiane ręcznie (workflow_dispatch), uruchamia `run_daily.py`, commituje wyniki i uploaduje logi jako artefakty

GitHub Actions nie stanowi części frontendu — służy wyłącznie do generowania danych.

## Istniejące pliki JSON w output/

| Plik | Opis |
|------|------|
| `status.json` | Główne dane statusu instrumentów (decyzje, poziomy, formacje, filary) |
| `ohlc.json` | Dane świecowe OHLC do wykresów (candles, markers, levels, harmonics) |
| `decisions_log.json` | Dziennik wszystkich podejmowanych decyzji |
| `classic_patterns.json` | Wykryte formacje klasyczne per symbol |
| `signals_history.json` | Historia sygnałów ze statusami (DETECTED, CONFIRMED, aktywacja, invalidation) |
| `ohlc_history.json` | Archiwum danych OHLC |

Format danych w tych plikach **nie wolno zmieniać**.

## Obecna aplikacja Streamlit (app.py)

Aplikacja desktopowa z widokami:
- **Dashboard** — kafelki instrumentów z decyzją, ceną, poziomami, przyciskiem „Wykres →”
- **Wykres** — wykres świecowy (Plotly) z markerami, poziomami entry/stop/target, formacjami harmonicznymi
- **Formacje** — tabela formacji harmonicznych, świecowych i klasycznych per instrument
- **Sygnały i historia** — tabela historii sygnałów i dziennika decyzji
- **Kalkulator XTB** — kalkulator pozycji dla instrumentów CFD (dźwignia, depozyt, zysk/strata, spread, swap, wynik netto)

## Obecna aplikacja HTML (frontend/index.html)

Aplikacja jednostronicowa, ciemny motyw, construida z:
- Nagłówek z logo, tytułem, statusem połączenia i przyciskiem odświeżania
- Sekcja „Instrumenty” — kafelki z symbolem, nazwą, kierunkiem (LONG/SHORT/BRAK), oceną sygnału /100
- Kliknięcie kafelka otwiera modal ze szczegółami instrumentu
- Stopka z zastrzeżeniem informacyjnym

## Sposób pobierania danych JSON przez frontend/index.html

Skrypt w `index.html` definiuje ścieżki względne do plików JSON:

```js
const PATHS = {
  decisions: '../output/decisions_log.json',
  status: '../output/status.json',
  chart: '../output/ohlc.json',
  classic: '../output/classic_patterns.json',
  signals: '../output/signals_history.json'
};
```

Dane są pobierane przez `fetch()` z cache `no-store` (parametr `?v=` + timestamp). Plik `status.json` jest wymagany; pozostałe są opcjonalne.

## Wykorzystanie Lightweight Charts

Biblioteka `lightweight-charts@4.2.2` ładowana z unpkg CDN. Używana w modalu szczegółów instrumentu do renderowania wykresu świecowego 4H z:
- Serią świecową (candlestick)
- Poziomami entry / stop / target jako linie poziome
- Markerami formacji harmonicznych
- ResizeObserver do dopasowywania wykresu do kontenera

## Istniejące funkcjonalności interfejsu HTML

Funkcjonalności obecnie zaimplementowane w `frontend/index.html`:

1. **Ładowanie danych** — pobieranie 5 plików JSON przy starcie aplikacji
2. **Status połączenia** — wskaźnik ładowania / błąd / dane załadowane
3. **Kafelki instrumentów** — wyświetlanie symbolu, nazwy, kierunku, oceny sygnału; sortowanie (BRAK na końcu, poiż po confidence malejąco)
4. **Odświeżanie danych** — przycisk odświeżania ponowne ładowanie wszystkich plików JSON
5. **Modal szczegółów instrumentu** — decyzja, wejście, SL, TP, stosunek zysku do ryzyka, ocena, filary (Renko/Harmoniczne/Świece), kontekst D1, ATR
6. **Wykres świecowy 4H** — Lightweight Charts z poziomami i markerami
7. **Formacje harmoniczne** — lista z ikonami, opisami i schematami SVG
8. **Formacje świecowe** — lista do 24 pozycji z opisami i schematami SVG
9. **Formacje klasyczne** — lista ostatnich 30 formacji z opisami i schematami SVG
10. **Uzasadnienie sygnału** — lista powodów (reasons) z决策
11. **Obsługa błędów** — komunikaty błędów ładowania danych, puste stany (empty-state)
14. **Responsywność** — media queries dla ekranów poniżej 800px i 430px
15. **Zamykanie modala** — przycisk ×, kliknięcie w tło, klawisz Escape

Niniejszy dokument opisuje wyłącznie funkcjonalności, które faktycznie istnieją. Nie dopisano funkcjonalności, których obecnie nie ma.