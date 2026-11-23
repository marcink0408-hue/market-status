# AGENTS.md — Market Status

## Czym jest Market Status

Market Status to platforma analizy rynku CFD (kontrakty różnic kursowych) działająca w interwale 4H.
Projekt generuje sygnały, wykrywa formacje (harmoniczne, świecowe, klasyczne)
oraz udostępnia kalkulator XTB. Dane pochodzą z silnika analitycznego Python i są zapisywane w
katalogu `output/` jako pliki JSON.

## Używane technologie

- **Python 3.12** — silnik analityczny (`app.py`, `run_daily.py`, `analysis/`, `config.py`, `data/`)
- **Streamlit** — istniejąca aplikacja desktopowa (`app.py`)
- **HTML + JavaScript** — obecny frontend (`frontend/index.html`) z biblioteką Lightweight Charts
- **GitHub Actions** — codzienne generowanie danych JSON (`.github/workflows/daily.yml`)
- **React + Vite** — nowy, docelowy frontend (`frontend-react/`), przygotowywany w ramach tej migracji
- **Tailwind CSS** — warstwa stylowania dla nowego frontendu (podstawowa konfiguracja)

## Elementy nienaruszalne

Następujące pliki i obszary projektu **nie mogą być modyfikowane** bez uprzedniej uzgodnienia:

- `frontend/index.html` — obecna aplikacja HTML pozostaje bez zmian jako punkt odniesienia
- `app.py` — aplikacja Streamlit, nie wolno jej modyfikować
- `analysis/` — cały silnik analityczny Python
- `data/` — moduł pobierania danych
- `config.py` — konfiguracja symboli, interwałów, parametrów formacji
- `run_daily.py` — skrypt generowania danych dziennych
- `output/*.json` — istniejące pliki danych wyjściowych (nie nadpisywać formatu ani zawartości)
- `.github/workflows/` — GitHub Actions, sposób generowania danych

## Zasady pracy

1. **Zakaz nieuzgodnionych zmian w Pythonie i GitHub Actions.** Silnik analityczny oraz sposób generowania danych pozostają nienaruszone przez cały okres migracji.
2. **Stopniowa migracja HTML do React.** Nowy frontend w `frontend-react/` rozwijany jest etapami. Każda istniejąca funkcjonalność HTML musi zostać odwzorowana w React, zachowując jej dotychczasowe działanie.
3. **Obowiązek zapoznania się z dokumentacją przed rozpoczęciem kolejnych etapów.** Przed przystąpieniem do prac nad kolejnym etapem należy przeczytać:
   - `docs/PROJECT.md` — rzeczywisty stan projektu
   - `docs/MASTER.md` — nadrzędna wizja docelowa
   - `docs/MIGRATION.md` — kolejność migracji
   - `docs/PROGRESS.md` — dziennik postępów (ostatni wpis)

## Kontekst projektu (obowiązkowe lektury)

- `docs/PROJECT.md`
- `docs/MASTER.md`
- `docs/MIGRATION.md`
- `docs/PROGRESS.md`