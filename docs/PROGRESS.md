# docs/PROGRESS.md — Dziennik postępów migracji Market Status

## 2026-11-25 — Panel decyzyjny i cykl życia sygnału

- Przebudowano istniejący React: ekran powitalny, nagłówek MARCIN – MÓJ XTB, dynamiczne GO, niebieskie ODŚWIEŻ, pięć kolumn instrumentów na desktopie i układ mobilny bez overflow.
- Główny sygnał znajduje się nad wykresem; panel zawiera tylko decyzję, aktualny status, poziomy, krótkie uzasadnienie, wykres, istotne formacje i trzy kafelki interwałów. Raporty ATR/Renko/XABCD/formacji klasycznych pozostają w silniku, nie w UI.
- Dodano `analysis/lifecycle.py`: PRZ, potwierdzenie D, target, negacja, wygaśnięcie oraz PENDING/ACTIVE/SL/TP. Terminy wynikają ze świec i długości nogi struktury; `can_enter=true` występuje tylko dla PENDING.
- Butterfly wymaga poprawnego D poza X; nieaktualne harmoniczne nie zasilają decyzji, a widok wykresu porządkuje oznaczenia po buforze 5 dni. Poziomy i markery pozostają przypisane do symbolu i interwału.
- Ceny są zaokrąglane wyłącznie w prezentacji. Dane `status.json` i `ohlc.json` zostały ponownie wygenerowane z rzeczywistego `run_daily.py`.
- Weryfikacja: 17 testów Python, 8 testów React, walidacja JSON, build Vite oraz test Chrome desktop/mobile: powitanie, 11 instrumentów, zmiany symbolu i 1H/4H/1D, GOLD, W20 1H, odświeżanie, GO, brak błędów konsoli i brak overflow przy 390 px. BTC nie występuje w obecnym źródle danych.

## 2026-11-24 — Analiza 1H / 4H / 1D i poprawka wykresu

- Wykres otrzymuje dane wyłącznie dla wybranego symbolu i interwału; serie XABCD są poprawnie usuwane i wyłączone z autoskalowania.
- Pipeline udostępnia rzeczywiste świece 1H, 4H agregowane z 1H oraz 1D, z pominięciem niezamkniętych świec. WIG20 ma awaryjną agregację dzienną według Europe/Warsaw.
- Ocena bazowa i kierunek pozostają na 4H; jawne wagi kontekstu 1D/1H korygują wynik bez głosowania kierunku i bez unieważniania go przez słaby 1H.
- Formacje, markery, ATR i kompletne zestawy Entry/SL/TP mają oznaczenie instrumentu lub interwału.
- Interfejs ma pełnoszeroką listę wszystkich instrumentów, dużą ocenę, pełnoszeroki wykres i szczegóły pod wykresem.
- Weryfikacja: 7 testów Python, 5 testów React, build Vite, walidacja JSON oraz test Chrome (instrumenty, interwały, zoom/pan, odświeżanie, mobile 390 px).

## Aktualny etap migracji

Etap 4 — Formacje i uzasadnienie sygnału

## Status etapu

Ukończony

## Wykonane zadania

- Zapoznanie się z dokumentacją i strukturą plików JSON (status.json, ohlc.json, signals_history.json) oraz kodem źródłowym Python (analysis/chart_data.py, analysis/decision.py)
- Przeczytanie oryginalnego `frontend/index.html` jako źródła prawdy dla logiki renderowania wykresu, poziomów i markerów
- Instalacja `lightweight-charts@4.2.2` (zgodna z wersją w oryginalnym HTML)
- Utworzenie `frontend-react/src/components/chart/PriceChart.jsx` — komponent wykresu świecowego Lightweight Charts z pełnym cyklem życia
- Utworzenie `frontend-react/src/components/details/DecisionDetails.jsx` — decyzyja, entry, SL, TP, R:R, confidence
- Utworzenie `frontend-react/src/components/details/SignalPillars.jsx` — trzy filary: Renko, Harmoniczne, Świece
- Utworzenie `frontend-react/src/components/details/MarketContext.jsx` — kontekst D1 i ATR(14)
- Przepisanie `frontend-react/src/components/details/InstrumentDetails.jsx` — komponent orquestrujący z danymi z status.json i ohlc.json
- Aktualizacja `frontend-react/src/components/instruments/InstrumentPanel.jsx` — przekazuje pełny obiekt instrumentu
- Aktualizacja `frontend-react/src/components/workspace/MainWorkspace.jsx` — używa PriceChart i InstrumentDetails
- Aktualizacja `frontend-react/src/App.jsx` — przekazuje `data` do MainWorkspace
- Dodanie zależności `lightweight-charts@4.2.2` do `package.json`
- Uruchomienie `npm run build` — zakończone pomyślnie (43 moduły, dist bez błędów)

### Etap 4 — Formacje i uzasadnienie sygnału

- Zapoznanie się z dokumentacją i strukturą plików JSON (status.json, classic_patterns.json) oraz oryginalnym `frontend/index.html`
- Utworzenie `frontend-react/src/components/details/HarmonicPatterns.jsx` — prezentacja formacji harmonicznych z opisami, poziomami X/A/B/C/D, schematem SVG XABCD
- Utworzenie `frontend-react/src/components/details/CandlePatterns.jsx` — prezentacja formacji świecowych z opisami, kierunkiem, czasem, siłą i diagramem SVG świec
- Utworzenie `frontend-react/src/components/details/ClassicPatterns.jsx` — prezentacja formacji klasycznych z `classic_patterns.json` z opisami, kierunkiem, ceną, czasem i schematem SVG
- Utworzenie `frontend-react/src/components/details/SignalJustification.jsx` — uzasadnienie sygnału z listą powodów (reasons), kontekstem D1 i ATR(14)
- Aktualizacja `frontend-react/src/components/details/InstrumentDetails.jsx` — dodanie nowych sekcji: formacje harmoniczne, świecowe, klasyczne, uzasadnienie sygnału
- Uruchomienie `npm run build` — zakończone pomyślnie (47 modułów, dist bez błędów)

## Utworzone i zmodyfikowane pliki

Utworzone:
- `frontend-react/src/components/chart/PriceChart.jsx`
- `frontend-react/src/components/details/DecisionDetails.jsx`
- `frontend-react/src/components/details/SignalPillars.jsx`
- `frontend-react/src/components/details/MarketContext.jsx`
- `frontend-react/src/components/details/HarmonicPatterns.jsx`
- `frontend-react/src/components/details/CandlePatterns.jsx`
- `frontend-react/src/components/details/ClassicPatterns.jsx`
- `frontend-react/src/components/details/SignalJustification.jsx`

Zmodyfikowane:
- `frontend-react/src/components/details/InstrumentDetails.jsx` — przepisany jako komponent orquestrujący; dodano sekcje formacji i uzasadnienia sygnału
- `frontend-react/src/components/instruments/InstrumentPanel.jsx` — przekazuje pełny obiekt instrumentu
- `frontend-react/src/components/workspace/MainWorkspace.jsx` — używa PriceChart i InstrumentDetails
- `frontend-react/src/App.jsx` — przekazuje `data` do MainWorkspace
- `frontend-react/package.json` — dodano `lightweight-charts@4.2.2`
- `docs/PROGRESS.md` — ten dziennik

## Zachowane funkcjonalności

Wszystkie istniejące funkcjonalności zachowane bez zmian:
- `frontend/index.html` — nienaruszony
- `app.py` — nienaruszony
- `data/` — nienaruszony
- `config.py` — nienaruszony
- `run_daily.py` — nienaruszony
- `.github/workflows/` — nienaruszone

Usunięte w ramach rezygnacji z backtestów:
- `analysis/backtest.py` — generator backtestów (nie był importowany przez inne moduły)
- `output/backtest_results.json` — plik wyników backtestu
- `frontend-react/src/components/stats/Statistics.jsx` — komponent statystyk backtestu w React

Zmodyfikowane:
- `analysis/` — usunięto `backtest.py` (pozostałe moduły nienaruszone)
- `output/*.json` — usunięto `backtest_results.json` (pozostałe pliki nienaruszone)

## Sposób pobierania danych

Wszystkie pięć plików JSON pobierane są przez `fetch()` z cache `no-store` (parametr `?v=` + timestamp). Ścieżki budowane z `import.meta.env.BASE_URL` + `output/<nazwa_pliku>`. Na GitHub Pages (`base: '/market-status/'`) prowadzi to do `/market-status/output/<plik>`. Lokalnie przez Vite dev serwer ścieżka `/output/` obsługiwana jest przez middleware serwujący pliki z `../output/`.

Dane OHLC, poziomy i markery harmoniczne pobierane są z `output/ohlc.json` (klucz `symbols[symbol]`), dane decyzyjne z `output/status.json`, formacje klasyczne z `output/classic_patterns.json`.

## Etap 5 — ANULOWANY

Etap 5 (Statystyki backtestu) został anulowany decyzją użytkownika. Funkcjonalność backtestów została usunięta z całego projektu:
- Usunięto `analysis/backtest.py`
- Usunięto `output/backtest_results.json`
- Usunięto `frontend-react/src/components/stats/Statistics.jsx`
- Usunięto odwołania do backtestu w `frontend-react/src/hooks/useMarketData.js` i `frontend-react/src/App.jsx`
- Zaktualizowana dokumentacja: `docs/MIGRATION.md`, `docs/PROJECT.md`, `docs/MASTER.md`, `AGENTS.md`

Pozostałe etapy (6, 7) zachowują swoją numerację i zakres bez zmian.

## Wynik kompilacji

`npm run build` — zakończone sukcesem, 47 modułów przekształconych, dist wygenerowany bez błędów:
- `dist/index.html` 0.50 kB
- `dist/assets/index-1RZW7d_u.css` 13.03 kB
- `dist/assets/index-BsuWgkme.js` 172.23 kB

## Nierozwiązane ograniczenia

- Brak danych OHLC dla niektórych instrumentów wyświetla komunikat zamiast wykresu (zgodnie z oryginałem)
- `ChartPlaceholder.jsx` z Etapu 2 nie jest już używany, ale pozostawiony bez zmian (nie usuwa się kodu z poprzednich etapów)
- Formacje klasyczne w `status.json` (pole `timeframes.4H.classic_patterns`) są puste dla wszystkich aktualnych instrumentów; dane klasyczne pochodzą wyłącznie z `output/classic_patterns.json`

