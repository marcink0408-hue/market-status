# docs/MIGRATION.md — Kolejność migracji HTML do React

## Zasady ogólne

- Migracja odbywa się etapami, zgodnie z `docs/PROGRESS.md`.
- Każda istniejąca funkcjonalność z `frontend/index.html` musi zostać uwzględniona w docelowym interfejsie React.
- Nie wolno utracić żadnej funkcjonalności.
- Nie modyfikujemy silnika Python ani formatu danych JSON.
- Nowy frontend odczytuje te same pliki JSON z katalogu `output/`.

## Etap 1 — Przygotowanie architektury i szkieletu (bieżący)

1. Utworzenie dokumentacji: `AGENTS.md`, `.clinerules/market-status.md`, `docs/PROJECT.md`, `docs/MASTER.md`, `docs/MIGRATION.md`, `docs/PROGRESS.md`.
2. Utworzenie katalogu `frontend-react/` z projektem React + Vite (JavaScript).
3. Podstawowa konfiguracja: Vite, Tailwind CSS, struktura komponentów.
4. Szkielet interfejsu: ciemny motyw, panel instrumentów, główny obszar roboczy, miejsce na wykres, szczegóły instrumentu, statystyki i sygnały, responsywny układ.
5. Kompilacja produkcyjna Vite (`npm run build`).
6. Potwierdzenie niezmienności istniejących plików HTML, Python, JSON i GitHub Actions.

## Etap 2 — Ładowanie danych i panel instrumentów

1. Implementacja pobierania plików JSON z `output/` (status, ohlc, decisions, classic, signals).
2. Wyświetlanie kafelków instrumentów z symbolem, nazwą, kierunkiem (LONG/SHORT/BRAK), oceną sygnału /100.
3. Status połączenia i przycisk odświeżania danych.
4. Sortowanie kafelków zgodnie z obecnym HTML (BRAK na końcu, potem po confidence malejąco).

## Etap 3 — Szczegóły instrumentu i wykres

1. Modal lub panel szczegółów instrumentu po kliknięciu kafelka.
2. Decyzja, wejście, stop loss, take profit, stosunek zysku do ryzyka, ocena sygnału.
3. Filary (Renko, Harmoniczne, Świece), kontekst D1, ATR.
4. Integracja Lightweight Charts dla wykresu świecowego 4H.
5. Poziomy entry/stop/target jako linie na wykresie.
6. Markery formacji harmonicznych na wykresie.

## Etap 4 — Formacje (ukończony)

1. Formacje harmoniczne z opisami i schematami — `HarmonicPatterns.jsx`.
2. Formacje świecowe z opisami i schematami — `CandlePatterns.jsx`.
3. Formacje klasyczne z opisami i schematami — `ClassicPatterns.jsx`.
4. Uzasadnienie sygnału (lista powodów) — `SignalJustification.jsx`.

## Etap 5 — Statystyki backtestu — ANULOWANY

Etap 5 został anulowany decyzją użytkownika. Funkcjonalność backtestów została usunięta z całego projektu (Python `analysis/backtest.py`, React `Statistics.jsx`, `output/backtest_results.json`). Nie implementuje się statystyk backtestu w React.

Pozostałe etapy (6, 7) zachowują swoją numerację i zakres bez zmian.

## Etap 6 — Kalkulator XTB

1. Przeniesienie kalkulatora XTB z `Kalkulator_XTB.html` do React.
2. Pełna funkcjonalność obliczeń: depozyt, zysk/strata, spread, swap, wynik netto.
3. Lista instrumentów z parametrami z `app.py`.

## Etap 7 — Finalizacja i walidacja

1. Porównanie funkcjonalności React z oryginalnym HTML.
2. Upewnienie się, że żadna funkcjonalność nie została utracona.
3. Kompilacja produkcyjna i weryfikacja działania.
4. Aktualizacja `docs/PROGRESS.md` jako ukończona migracja.

## Źródło danych

Wszystkie etapy odczytują dane z tych samych plików JSON:
- `output/status.json` — główne dane instrumentów
- `output/ohlc.json` — dane wykresów
- `output/decisions_log.json` — dziennik decyzji
- `output/classic_patterns.json` — formacje klasyczne
- `output/signals_history.json` — historia sygnałów