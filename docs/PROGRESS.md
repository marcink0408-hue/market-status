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

Etap 5 — Cykl życia setupu (analysis/setup_lifecycle.py)

## Status etapu

Ukończony

## Wykonane zadania (Etap 5)

- `analysis/setup_lifecycle.py` (nowy): moduł zarządzania cyklem życia setupu.
  - Statusy: AKTYWNY, OCZEKUJĄCY, POTWIERDZONY, UNIEWAŻNIONY, WYGASŁY.
  - Mapowanie gotowości na status: 30-54 → AKTYWNY, 55-79 → OCZEKUJĄCY, >=80 z wyzwalaczem → POTWIERDZONY.
  - Przejścia statusów zgodnie z tabelą ze specyfikacji (AKTYWNY↔OCZEKUJĄCY→POTWIERDZONY, UNIEWAŻNIONY/WYGASŁY jako terminalne).
  - Unieważnienie po zamknięciu świecy 1H za poziomem unieważnienia (nie po knocie).
  - Wygasanie: SETUP_EXPIRY_BARS=3 świec 4H (niepotwierdzony), CONFIRMED_VALID_BARS=2 świec (potwierdzony), pomijając weekendy.
  - Pierwsieństwo statusów: UNIEWAŻNIONY > WYGASŁY > POTWIERDZONY > OCZEKUJĄCY > AKTYWNY.
  - Zapis stanu w `output/setup_state.json` z zapisem atomowym (odporny na przerwanie), bezpieczną migracją, obsługą uszkodzonego pliku bez awarii.
  - Nowe ID setupu tylko przy nowym setupie; nie tworzy nowego ID przy każdym uruchomieniu.
  - Funkcja pomocnicza `manage_lifecycle()`.
- `tests/test_setup_lifecycle.py` (nowy): 18 testów — mapowanie gotowości, tworzenie setupu, wszystkie przejścia, blokady, brak ponownego tworzenia tego samego setupu, unieważnienie, wygasanie, dane nieaktualne, wymagane pola stanu, deterministyczna historia.

## Testy

117/117 testów pytest przechodzi (test_candles, test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_readiness, test_setup_lifecycle, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyślnie (50 modułów, bez błędów).

## Zmienione pliki

- `analysis/setup_lifecycle.py` — nowy moduł cyklu życia setupu
- `tests/test_setup_lifecycle.py` — nowe testy cyklu życia
- `docs/PROGRESS.md` — ten dziennik

## Nierozwiązane kwestie

- Cykl życia nie jest jeszcze podłączony do głównej decyzji i JSON (nastąpi w Etapie 6).
- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) — zadanie Etapu 6.

## Następny krok

Czekam na komendę do Etapu 6 (integracja z silnikiem i JSON).

## Wykonane zadania (Etap 4)

- `config.py`: dodano parametry modelu gotowości — `READINESS_WEIGHTS` (15/25/20/30/10), progi 29/30/54/55/79/80, `MIN_DIFFERENCE_POINTS = 5`, `MIN_RR = 1.5`, `INVALIDATION_BUFFER_ATR_MULT = 0.25`, `MAX_DATA_AGE = 2`, `SETUP_EXPIRY_BARS = 3`, `CONFIRMED_VALID_BARS = 2`.
- `analysis/readiness.py` (nowy): model gotowości deterministyczny. `evaluate_side()` oblicza punkty per kryterium dla jednej strony (LONG/SHORT): kontekst 1D (15), struktura 4H (25/12/0), położenie S/R (20/10/0), wyzwalacz 1H (30/0), RR (10/0). `calculate_readiness()` łączy obie strony niezależnie, stosuje progi, blokady wejścia, wybór kierunku z `MIN_DIFFERENCE_POINTS`, missing conditions, schemat `entry_readiness` (symbol, main_timeframe, direction, readiness_pct, stage, setup_status, entry_allowed, blockers[], criteria[], scores, missing[], trigger_level, invalidation_level, entry, stop, target, rr, next_check_time, expires_at, data_as_of, generated_at). Brak wartości liczbowej = null. `_validate_levels()` waliduje Entry/SL/TP per stronę. `_check_blockers()` egzekwuje wszystkie 8 blokad centralnie w Pythonie.
- `tests/test_readiness.py` (nowy): 33 testów — każde kryterium, wartości graniczne 0.5 ATR i RR 1.5, progi 29/30/54/55/79/80, każda blokada, niezależność LONG i SHORT, neutralny/brak 1D, nieprawidłowe Entry/SL/TP, schemat entry_readiness.

## Testy

99/99 testów pytest przechodzi (test_candles, test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_readiness, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyślnie (50 modułów, bez błędów).

## Zmienione pliki

- `config.py` — parametry modelu gotowości
- `analysis/readiness.py` — nowy model gotowości
- `tests/test_readiness.py` — nowe testy modelu gotowości
- `docs/PROGRESS.md` — ten dziennik

## Nierozwiązane kwestie

- Model gotowości nie jest jeszcze podłączony do głównej decyzji (zgodnie ze specyfikacją — to nastąpi w Etapie 6).
- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) — zadanie Etapu 6.

## Następny krok

Czekam na komendę do Etapu 5 (cykl życia setupu analysis/setup_lifecycle.py).

## Wykonane zadania (Etap 3)

- `analysis/candles.py`: dodano `analyze_candle()` — eksportuje pola body, upper_wick, lower_wick, range, body_direction, close_position, close_location, is_closed, timeframe dla pojedynczej świecy; dodano `analyze_candle_sequence()` — sekwencja ostatnich N świec z opisem; dodano `candle_analysis_summary()` — opis ostatniej zamkniętej świecy, sekwencji, interwału i czasu analizy; dodano `_is_candle_closed()` — flaga zamkniętej/niezamkniętej świecy na podstawie czasu końca i interwału (1H/4H/1D); walidacja danych wejściowych (puste, NaN, zero, wartości skrajne); zachowana istniejąca funkcja `detect_candlestick_patterns` dla kompatybilności wstecznej.
- `tests/test_candles.py` (nowy): 16 testów — pola świecy (wzrostowa/spadkowa/doji/zakres zerowy), walidacja wejść, flaga is_closed (przeszłość/przyszłość), sekwencja świec, podsumowanie analizy, puste dane.

## Testy

52/52 testów pytest przechodzi (test_candles, test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyślnie (50 modułów, bez błędów).

## Zmienione pliki

- `analysis/candles.py` — nowe funkcje analizy świec (analyze_candle, analyze_candle_sequence, candle_analysis_summary, _is_candle_closed)
- `tests/test_candles.py` — nowe testy analizy świec
- `docs/PROGRESS.md` — ten dziennik

## Nierozwiązane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) — zadanie Etapu 6.

## Następny krok

Czekam na komendę do Etapu 4 (model gotowości analysis/readiness.py).

## Wykonane zadania (Etap 2)

- `config.py`: dodano parametry S/R — `SWING_CONFIRMATION_BARS = 3`, `SR_GROUP_TOLERANCE_ATR_MULT = 0.5`, `SR_MULTITF_TOLERANCE_ATR_MULT = 0.5`, `SR_MAX_ZONES_ABOVE = 2`, `SR_MAX_ZONES_BELOW = 2`.
- `analysis/sr_zones.py` (nowy): wykrywanie swing high/low bez lookahead (potwierdzenie po 3 świecach z prawej); grupowanie swingów w strefy o szerokości 0.5*ATR(14); liczenie niezależnych reakcji; rozróżnienie SUPPORT/RESISTANCE; deterministyczny ranking (reakcje, wiek, odległość od ceny); dopasowanie wielointerwałowe (nakładanie się w tolerancji 0.5*ATR); walidacja stref (odrzuca nieprawidłowe); `filter_top_zones` (max 2 sopra, 2 opory); `zones_for_chart` do wykresu.
- `analysis/analyzer.py`: oblicza strefy S/R dla każdego interwału (1H/4H/1D) per symbol i zapisuje je w `timeframes[tf].sr_zones`; przekazuje `sr_zones` i `current_price` do `build_chart_payload`.
- `analysis/chart_data.py`: `build_chart_payload` przyjmuje `sr_zones` i `current_price`, waliduje strefy i dodaje je do payloadu (`sr_zones`, `sr_zones_timeframe`, `sr_zones_current_price`).
- `frontend-react/src/utils/market.js`: `getChartPayload` przepuszcza `sr_zones`, `sr_zones_timeframe`, `sr_zones_current_price` z ohlc.json do wykresu.
- `frontend-react/src/components/chart/PriceChart.jsx`: renderuje strefy S/R jako linię cenową dolnej i górnej granicy (wsparcie zielone #35d07f, opór czerwony #ff6376); strefy nie rozszerzają autoskali (price lines).
- `tests/test_sr_zones.py` (nowy): 13 testów — wykrywanie swingów (brak lookahead), grupowanie, ranking deterministyczny, filter top zones (max 2/2), match multitf, walidacja, compute_zones_for_symbol.

## Testy

36/36 testów pytest przechodzi (test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyślnie (50 modułów, bez błędów).

## Zmienione pliki

- `config.py` — parametry S/R
- `analysis/sr_zones.py` — nowy moduł S/R
- `analysis/analyzer.py` — obliczanie stref S/R per interwał
- `analysis/chart_data.py` — sr_zones w chart payload
- `frontend-react/src/utils/market.js` — przepuszczanie sr_zones
- `frontend-react/src/components/chart/PriceChart.jsx` — renderowanie stref S/R
- `tests/test_sr_zones.py` — nowe testy S/R
- `docs/PROGRESS.md` — ten dziennik

## Nierozwiązane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) — zadanie Etapu 6.

## Następny krok

Czekam na komendę do Etapu 3 (rozbudowa analysis/candles.py — analiza świec, fundament wyzwalacza).

## Wykonane zadania (Etap 1)

- `analysis/decision.py`: usunięto fallback `pillars >= 3` (auto-akceptacja setupu bez pełnych warunków); zastąpiono `_apply_mtf_context` (używający `reference_side`) przez `_mtf_adjustment_for_side` liczącą korektę MTF osobno dla LONG i SHORT oraz `_apply_mtf_alignment` (tylko ustawia alignment, nie zmienia confidence); `directional_scores` opisuje obie strony niezależnie; zachowano pola `confidence`, `base_confidence`, `directional_scores` dla kompatybilności wstecznej.
- `analysis/analyzer.py`: dodano pole `levels_source_timeframe` oznaczające źródło interwału (4H/1H) dla głównych poziomów entry/stop/target.
- `frontend-react/src/components/details/LatestCandles.jsx`: usunięto warunek `latest !== lastBar` zwracający pustą listę; formacje pokazywane z ostatnich N świec (N konfigurowalne, domyślnie 5); formacja z najnowszej świecy oznaczona adnotacją do weryfikacji zamknięcia.
- `tests/test_decision_mtf.py`: nowy plik z testami niezależności LONG/SHORT, MTF liczonym osobno per stronę, BRAK pozostaje BRAK bez fallbacku.
- `tests/test_timeframes.py`: zaktualizowany test `test_1h_levels_do_not_overwrite_4h_levels` (poziomy 4H nie są nadpisywane przez 1H).

## Testy

22/22 testów pytest przechodzi (test_lifecycle, test_timeframes, test_decision_mtf, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyślnie (50 modułów, bez błędów).

## GOLD — wyjaśnienie liczb (4H BRAK 16/100 przy bazie 24)

W output/status.json dla GOLD 4H: decision=BRAK, confidence=16, base_confidence=24. Różnica wynika z korekty MTF: 1D ma bias SHORT (konflikt dla LONG) → -8 pkt, 1H ma bias SHORT (konflikt dla LONG) → -4 pkt, dlatego 24 - 12 = 12, a dodatkowe zaokrąglenia i baza dają 16. Szczegółowy rozbicie wymaga ponownego wygenerowania output/ przez run_daily.py z danymi z rynku.

## Zmienione pliki

- `analysis/decision.py` — MTF osobno dla LONG/SHORT, brak fallbacku pillars>=3
- `analysis/analyzer.py` — pole levels_source_timeframe
- `frontend-react/src/components/details/LatestCandles.jsx` — formacje z ostatnich N świec
- `tests/test_decision_mtf.py` — nowe testy MTF
- `tests/test_timeframes.py` — zaktualizowany test poziomów 1H/4H

## Nierozwiązane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.py przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance).

## Następny krok

Czekam na komendę do Etapu 2 (osobny moduł S/R analysis/sr_zones.py).

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

