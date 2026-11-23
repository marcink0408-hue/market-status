# docs/MASTER.md — Nadrzędna wizja docelowego Market Status

## React + Vite jako docelowy frontend

Nowy frontend budowany w katalogu `frontend-react/` z użyciem React + Vite w JavaScript.
Zastosowano Tailwind CSS jako warstwę stylowania. Aplikacja ma być samodzielnym interfejsem
odczytującym dane JSON z katalogu `output/` (ten sam format, co obecny frontend HTML).

## Python jako silnik analityczny

Silnik Python (`run_daily.py`, `analysis/`, `config.py`, `data/`) pozostaje niezmieniony.
Wszystkie obliczenia, wykrywanie formacji i decyzje handlowe są generowane przez Python.
React nie wprowadza własnej logiki analitycznej — wyłącznie wyświetla dane wyprodukowane przez Python.

## Zachowanie istniejących obliczeń i logiki analitycznej

Wszystkie funkcjonalności obecnego HTML muszą zostać odwzorowane w React:
- Kafelki instrumentów z decyzją i oceną sygnału
- Szczegóły instrumentu (entry, stop, target, R:R, confidence, filary)
- Wykres świecowy 4H (docelowo Lightweight Charts w React)
- Formacje harmoniczne, świecowe, klasyczne
- Uzasadnienie sygnału
- Kalkulator XTB

## Profesjonalny interfejs platformy analizy CFD

Docelowy interfejs ma charakter profesjonalnej platformy analizy CFD:
- Ciemny motyw
- Panel instrumentów po lewej
- Główny obszar roboczy z wykresem i szczegółami
- Sekcje statystyk i sygnałów
- Responsywny układ dostosowujący się do rozmiaru ekranu

## Rozwijanie wykresów, formacji, sygnałów i statystyk

Każda sekcja ma być rozwijalna w kolejnych etapach migracji. Brak fikcyjnych danych —
wszystkie informacje pochodzą z plików JSON w `output/`.

## Zachowanie kalkulatora XTB

Kalkulator XTB (obecnie w `Kalkulator_XTB.html` i jako widok w Streamlit) musi zostać
przeniesiony do React w ramach późniejszego etapu migracji, zachowując pełną funkcjonalność
obliczeń (depozyt, zysk/strata, spread, swap, wynik netto).

## Możliwość późniejszego rozwoju o kolejne funkcjonalności

Architektura React + Vite umożliwia dodawanie nowych funkcjonalności bez naruszania
istniejącego silnika Pythona. Migracja odbywa się etapami, zgodnie z `docs/MIGRATION.md`.