# docs/PROGRESS.md â€” Dziennik postÄ™pĂłw migracji Market Status

## 2026-11-25 â€” Panel decyzyjny i cykl ĹĽycia sygnaĹ‚u

- Przebudowano istniejÄ…cy React: ekran powitalny, nagĹ‚Ăłwek MARCIN â€“ MĂ“J XTB, dynamiczne GO, niebieskie ODĹšWIEĹ», piÄ™Ä‡ kolumn instrumentĂłw na desktopie i ukĹ‚ad mobilny bez overflow.
- GĹ‚Ăłwny sygnaĹ‚ znajduje siÄ™ nad wykresem; panel zawiera tylko decyzjÄ™, aktualny status, poziomy, krĂłtkie uzasadnienie, wykres, istotne formacje i trzy kafelki interwaĹ‚Ăłw. Raporty ATR/Renko/XABCD/formacji klasycznych pozostajÄ… w silniku, nie w UI.
- Dodano `analysis/lifecycle.py`: PRZ, potwierdzenie D, target, negacja, wygaĹ›niÄ™cie oraz PENDING/ACTIVE/SL/TP. Terminy wynikajÄ… ze Ĺ›wiec i dĹ‚ugoĹ›ci nogi struktury; `can_enter=true` wystÄ™puje tylko dla PENDING.
- Butterfly wymaga poprawnego D poza X; nieaktualne harmoniczne nie zasilajÄ… decyzji, a widok wykresu porzÄ…dkuje oznaczenia po buforze 5 dni. Poziomy i markery pozostajÄ… przypisane do symbolu i interwaĹ‚u.
- Ceny sÄ… zaokrÄ…glane wyĹ‚Ä…cznie w prezentacji. Dane `status.json` i `ohlc.json` zostaĹ‚y ponownie wygenerowane z rzeczywistego `run_daily.py`.
- Weryfikacja: 17 testĂłw Python, 8 testĂłw React, walidacja JSON, build Vite oraz test Chrome desktop/mobile: powitanie, 11 instrumentĂłw, zmiany symbolu i 1H/4H/1D, GOLD, W20 1H, odĹ›wieĹĽanie, GO, brak bĹ‚Ä™dĂłw konsoli i brak overflow przy 390 px. BTC nie wystÄ™puje w obecnym ĹşrĂłdle danych.

## 2026-11-24 â€” Analiza 1H / 4H / 1D i poprawka wykresu

- Wykres otrzymuje dane wyĹ‚Ä…cznie dla wybranego symbolu i interwaĹ‚u; serie XABCD sÄ… poprawnie usuwane i wyĹ‚Ä…czone z autoskalowania.
- Pipeline udostÄ™pnia rzeczywiste Ĺ›wiece 1H, 4H agregowane z 1H oraz 1D, z pominiÄ™ciem niezamkniÄ™tych Ĺ›wiec. WIG20 ma awaryjnÄ… agregacjÄ™ dziennÄ… wedĹ‚ug Europe/Warsaw.
- Ocena bazowa i kierunek pozostajÄ… na 4H; jawne wagi kontekstu 1D/1H korygujÄ… wynik bez gĹ‚osowania kierunku i bez uniewaĹĽniania go przez sĹ‚aby 1H.
- Formacje, markery, ATR i kompletne zestawy Entry/SL/TP majÄ… oznaczenie instrumentu lub interwaĹ‚u.
- Interfejs ma peĹ‚noszerokÄ… listÄ™ wszystkich instrumentĂłw, duĹĽÄ… ocenÄ™, peĹ‚noszeroki wykres i szczegĂłĹ‚y pod wykresem.
- Weryfikacja: 7 testĂłw Python, 5 testĂłw React, build Vite, walidacja JSON oraz test Chrome (instrumenty, interwaĹ‚y, zoom/pan, odĹ›wieĹĽanie, mobile 390 px).

## Aktualny etap migracji

Etap 7 â€” Interfejs uĹĽytkownika

## Status etapu

UkoĹ„czony

## Wykonane zadania (Etap 7)

- `frontend-react/src/components/details/SetupSummary.jsx` (nowy): panel gĹ‚Ăłwny wyĹ›wietlajÄ…cy wyĹ‚Ä…cznie dane `entry_readiness` z JSON:
  1. Instrument i gĹ‚Ăłwny interwaĹ‚
  2. Kierunek: LONG / SHORT / BRAK KIERUNKU (z kolorem)
  3. Etap setupu (BRAK KIERUNKU / OBSERWUJ / PRZYGOTOWANIE / KANDYDAT DO WEJĹšCIA)
  4. "GotowoĹ›Ä‡ setupu: X%" z adnotacjÄ… ĹĽe to nie szansa na zysk
  5. NajwaĹĽniejszy brakujÄ…cy warunek (pierwszy z listy missing)
  6. Poziom uniewaĹĽnienia
  7. Status setupu (AKTYWNY / OCZEKUJÄ„CY / POTWIERDZONY / UNIEWAĹ»NIONY / WYGASĹY)
  8. NajbliĹĽsza ocena warunkĂłw (next_check_time)
  9. "Dane z:" z rzeczywistym czasem (data_as_of)
  10. ZgodnoĹ›Ä‡ interwaĹ‚Ăłw: 1D â€” kierunek, 4H â€” setup, 1H â€” wyzwalacz
  - Przy POTWIERDZONY: "Warunki setupu speĹ‚nione. To nie jest rekomendacja inwestycyjna."
  - Przy entry_allowed: Entry, SL, TP, RR
  - StaĹ‚a adnotacja: "NarzÄ™dzie analityczne, nie rekomendacja inwestycyjna."
  - Bezpieczna obsĹ‚uga braku entry_readiness (komunikat zamiast pozornych wartoĹ›ci)
  - React wyĹ‚Ä…cznie wyĹ›wietla dane, nie przelicza gotowoĹ›ci ani nie egzekwuje blokad
- `frontend-react/src/components/details/InstrumentDetails.jsx`: dodano SetupSummary na gĂłrze sekcji detali

## Testy

117/117 testĂłw pytest przechodzi (test_candles, test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_readiness, test_setup_lifecycle, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyĹ›lnie (51 moduĹ‚Ăłw, bez bĹ‚Ä™dĂłw).

## Zmienione pliki

- `frontend-react/src/components/details/SetupSummary.jsx` â€” nowy komponent panelu gĹ‚Ăłwnego
- `frontend-react/src/components/details/InstrumentDetails.jsx` â€” dodano SetupSummary
- `docs/PROGRESS.md` â€” ten dziennik

## NierozwiÄ…zane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance).

## Etap 8 â€” Testy koĹ„cowe i odbiĂłr (ukoĹ„czony)

## Status etapu

UkoĹ„czony

## Wyniki kontroli integracyjnej (Etap 8)

- **8A Logika**: 117 testĂłw pytest â€” niezaleĹĽnoĹ›Ä‡ LONG/SHORT, MTF bez przenoszenia punktĂłw miÄ™dzy kierunkami, neutralny 1D nie blokuje kierunku, brak danych nie wymusza kierunku, BRAK KIERUNKU nie zamienia siÄ™ w sygnaĹ‚, gotowoĹ›Ä‡ nie omija ĹĽadnej blokady, RR poniĹĽej 1.5 blokuje wejĹ›cie, brak wyzwalacza blokuje wejĹ›cie, nieaktualne/niekompletne dane blokujÄ… wejĹ›cie, uniewaĹĽnienie blokuje wejĹ›cie, wygaĹ›niÄ™cie blokuje wejĹ›cie, niezamkniÄ™ta Ĺ›wieca nie jest wyzwalaczem, POTWIERDZONY tylko po speĹ‚nieniu wszystkich warunkĂłw.
- **8B S/R**: test_sr_zones.py â€” swingi bez lookahead, grupowanie 0.5*ATR, liczba niezaleĹĽnych reakcji, ranking deterministyczny, wsparcie i opĂłr, dopasowanie wielointerwaĹ‚owe (nakĹ‚adanie siÄ™ w tolerancji 0.5*ATR).
- **8C Wykres**: PriceChart.jsx renderuje strefy S/R (price lines bez rozszerzania autoskali), markery filtrowane przez identityMatches (symbol + interwaĹ‚), brak starych markerĂłw i poziomĂłw po zmianie instrumentu/danych.
- **8D Instrumenty i interwaĹ‚y**: validate_output.py â€” wszystkie 11 instrumentĂłw z config.SYMBOLS (w20, us500, gold, silver, eurpln, eurusd, usdpln, usdjpy, copper, eu50, uk100), wszystkie 3 interwaĹ‚y (1H, 4H, 1D). GOLD jako pierwszy instrument do kontroli.
- **8E Kontrola techniczna**: testy jednostkowe 117/117 âś“, testy integracyjne Pythonâ†’JSON (validate_output.py) âś“, walidacja JSON âś“, produkcyjny build Vite (51 moduĹ‚Ăłw, bez bĹ‚Ä™dĂłw) âś“.
- **8F Kryteria ukoĹ„czenia**: wszystkie speĹ‚nione â€” wszystkie instrumenty analizowane, MTF ocenia LONG/SHORT niezaleĹĽnie, rzeczywisty moduĹ‚ S/R (analysis/sr_zones.py), setup ma kierunek/getowoĹ›Ä‡/etap/cykl ĹĽycia, blokady egzekwowane w Pythonie, silnik wyjaĹ›nia brakujÄ…ce warunki, nieaktualne/uniewaĹĽnione/wygasĹ‚e setupy nie pokazywane jako aktywne, wykres pokazuje wĹ‚aĹ›ciwe dane dla wĹ‚aĹ›ciwego instrumentu i interwaĹ‚u, frontend pokazuje jednÄ… czytelnÄ… informacjÄ™ gĹ‚ĂłwnÄ… i szczegĂłĹ‚y na ĹĽÄ…danie, testy przechodzÄ…, build przechodzi.

## Ograniczenia Etapu 8 (brak Ĺ›rodowiska)

- Nie moĹĽna uruchomiÄ‡ yfinance (brak sieci w tym Ĺ›rodowisku) â€” nie wygenerowano nowych output/ przez run_daily.py.
- Nie moĹĽna uruchomiÄ‡ przeglÄ…darki Chrome â€” brak kontroli w przeglÄ…darce, responsywnoĹ›ci i bĹ‚Ä™dĂłw konsoli.
- Nie moĹĽna opublikowaÄ‡ na GitHub Pages â€” brak dostÄ™pu do GitHub Actions z tego Ĺ›rodowiska.

## Zmienione pliki w Etapie 8

Brak nowych zmian kodu â€” wyĹ‚Ä…cznie weryfikacja istniejÄ…cego kodu.

## Stan koĹ„cowy projektu

Wszystkie 7 etapy wykonane i zaakceptowane. Projekt gotowy do dalszych prac (np. Etap 10A â€” Prawdziwy wyzwalacz 1H zakoĹ„czony: wyzwalacz 1H opiera siÄ™ na rzeczywistym zamkniÄ™ciu Ĺ›wiecy 1H (wariant A: wybicie poziomu S/R; wariant B: formacja w strefie â‰¤0.5 ATR), nie na statusie PENDING/ACTIVE. LONG i SHORT oceniane niezaleĹĽnie. Projekt gotowy do dalszych prac (Etapy 10B-10D oczekujÄ… na komendÄ™).


## Wykonane zadania (Etap 4)

- `config.py`: dodano parametry modelu gotowoĹ›ci â€” `READINESS_WEIGHTS` (15/25/20/30/10), progi 29/30/54/55/79/80, `MIN_DIFFERENCE_POINTS = 5`, `MIN_RR = 1.5`, `INVALIDATION_BUFFER_ATR_MULT = 0.25`, `MAX_DATA_AGE = 2`, `SETUP_EXPIRY_BARS = 3`, `CONFIRMED_VALID_BARS = 2`.
- `analysis/readiness.py` (nowy): model gotowoĹ›ci deterministyczny. `evaluate_side()` oblicza punkty per kryterium dla jednej strony (LONG/SHORT): kontekst 1D (15), struktura 4H (25/12/0), poĹ‚oĹĽenie S/R (20/10/0), wyzwalacz 1H (30/0), RR (10/0). `calculate_readiness()` Ĺ‚Ä…czy obie strony niezaleĹĽnie, stosuje progi, blokady wejĹ›cia, wybĂłr kierunku z `MIN_DIFFERENCE_POINTS`, missing conditions, schemat `entry_readiness` (symbol, main_timeframe, direction, readiness_pct, stage, setup_status, entry_allowed, blockers[], criteria[], scores, missing[], trigger_level, invalidation_level, entry, stop, target, rr, next_check_time, expires_at, data_as_of, generated_at). Brak wartoĹ›ci liczbowej = null. `_validate_levels()` waliduje Entry/SL/TP per stronÄ™. `_check_blockers()` egzekwuje wszystkie 8 blokad centralnie w Pythonie.
- `tests/test_readiness.py` (nowy): 33 testĂłw â€” kaĹĽde kryterium, wartoĹ›ci graniczne 0.5 ATR i RR 1.5, progi 29/30/54/55/79/80, kaĹĽda blokada, niezaleĹĽnoĹ›Ä‡ LONG i SHORT, neutralny/brak 1D, nieprawidĹ‚owe Entry/SL/TP, schemat entry_readiness.

## Testy

99/99 testĂłw pytest przechodzi (test_candles, test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_readiness, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyĹ›lnie (50 moduĹ‚Ăłw, bez bĹ‚Ä™dĂłw).

## Zmienione pliki

- `config.py` â€” parametry modelu gotowoĹ›ci
- `analysis/readiness.py` â€” nowy model gotowoĹ›ci
- `tests/test_readiness.py` â€” nowe testy modelu gotowoĹ›ci
- `docs/PROGRESS.md` â€” ten dziennik

## NierozwiÄ…zane kwestie

- Model gotowoĹ›ci nie jest jeszcze podĹ‚Ä…czony do gĹ‚Ăłwnej decyzji (zgodnie ze specyfikacjÄ… â€” to nastÄ…pi w Etapie 6).
- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) â€” zadanie Etapu 6.

## NastÄ™pny krok

Czekam na komendÄ™ do Etapu 5 (cykl ĹĽycia setupu analysis/setup_lifecycle.py).

## Wykonane zadania (Etap 3)

- `analysis/candles.py`: dodano `analyze_candle()` â€” eksportuje pola body, upper_wick, lower_wick, range, body_direction, close_position, close_location, is_closed, timeframe dla pojedynczej Ĺ›wiecy; dodano `analyze_candle_sequence()` â€” sekwencja ostatnich N Ĺ›wiec z opisem; dodano `candle_analysis_summary()` â€” opis ostatniej zamkniÄ™tej Ĺ›wiecy, sekwencji, interwaĹ‚u i czasu analizy; dodano `_is_candle_closed()` â€” flaga zamkniÄ™tej/niezamkniÄ™tej Ĺ›wiecy na podstawie czasu koĹ„ca i interwaĹ‚u (1H/4H/1D); walidacja danych wejĹ›ciowych (puste, NaN, zero, wartoĹ›ci skrajne); zachowana istniejÄ…ca funkcja `detect_candlestick_patterns` dla kompatybilnoĹ›ci wstecznej.
- `tests/test_candles.py` (nowy): 16 testĂłw â€” pola Ĺ›wiecy (wzrostowa/spadkowa/doji/zakres zerowy), walidacja wejĹ›Ä‡, flaga is_closed (przeszĹ‚oĹ›Ä‡/przyszĹ‚oĹ›Ä‡), sekwencja Ĺ›wiec, podsumowanie analizy, puste dane.

## Testy

52/52 testĂłw pytest przechodzi (test_candles, test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyĹ›lnie (50 moduĹ‚Ăłw, bez bĹ‚Ä™dĂłw).

## Zmienione pliki

- `analysis/candles.py` â€” nowe funkcje analizy Ĺ›wiec (analyze_candle, analyze_candle_sequence, candle_analysis_summary, _is_candle_closed)
- `tests/test_candles.py` â€” nowe testy analizy Ĺ›wiec
- `docs/PROGRESS.md` â€” ten dziennik

## NierozwiÄ…zane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) â€” zadanie Etapu 6.

## NastÄ™pny krok

Czekam na komendÄ™ do Etapu 4 (model gotowoĹ›ci analysis/readiness.py).

## Wykonane zadania (Etap 2)

- `config.py`: dodano parametry S/R â€” `SWING_CONFIRMATION_BARS = 3`, `SR_GROUP_TOLERANCE_ATR_MULT = 0.5`, `SR_MULTITF_TOLERANCE_ATR_MULT = 0.5`, `SR_MAX_ZONES_ABOVE = 2`, `SR_MAX_ZONES_BELOW = 2`.
- `analysis/sr_zones.py` (nowy): wykrywanie swing high/low bez lookahead (potwierdzenie po 3 Ĺ›wiecach z prawej); grupowanie swingĂłw w strefy o szerokoĹ›ci 0.5*ATR(14); liczenie niezaleĹĽnych reakcji; rozrĂłĹĽnienie SUPPORT/RESISTANCE; deterministyczny ranking (reakcje, wiek, odlegĹ‚oĹ›Ä‡ od ceny); dopasowanie wielointerwaĹ‚owe (nakĹ‚adanie siÄ™ w tolerancji 0.5*ATR); walidacja stref (odrzuca nieprawidĹ‚owe); `filter_top_zones` (max 2 sopra, 2 opory); `zones_for_chart` do wykresu.
- `analysis/analyzer.py`: oblicza strefy S/R dla kaĹĽdego interwaĹ‚u (1H/4H/1D) per symbol i zapisuje je w `timeframes[tf].sr_zones`; przekazuje `sr_zones` i `current_price` do `build_chart_payload`.
- `analysis/chart_data.py`: `build_chart_payload` przyjmuje `sr_zones` i `current_price`, waliduje strefy i dodaje je do payloadu (`sr_zones`, `sr_zones_timeframe`, `sr_zones_current_price`).
- `frontend-react/src/utils/market.js`: `getChartPayload` przepuszcza `sr_zones`, `sr_zones_timeframe`, `sr_zones_current_price` z ohlc.json do wykresu.
- `frontend-react/src/components/chart/PriceChart.jsx`: renderuje strefy S/R jako liniÄ™ cenowÄ… dolnej i gĂłrnej granicy (wsparcie zielone #35d07f, opĂłr czerwony #ff6376); strefy nie rozszerzajÄ… autoskali (price lines).
- `tests/test_sr_zones.py` (nowy): 13 testĂłw â€” wykrywanie swingĂłw (brak lookahead), grupowanie, ranking deterministyczny, filter top zones (max 2/2), match multitf, walidacja, compute_zones_for_symbol.

## Testy

36/36 testĂłw pytest przechodzi (test_lifecycle, test_timeframes, test_decision_mtf, test_sr_zones, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyĹ›lnie (50 moduĹ‚Ăłw, bez bĹ‚Ä™dĂłw).

## Zmienione pliki

- `config.py` â€” parametry S/R
- `analysis/sr_zones.py` â€” nowy moduĹ‚ S/R
- `analysis/analyzer.py` â€” obliczanie stref S/R per interwaĹ‚
- `analysis/chart_data.py` â€” sr_zones w chart payload
- `frontend-react/src/utils/market.js` â€” przepuszczanie sr_zones
- `frontend-react/src/components/chart/PriceChart.jsx` â€” renderowanie stref S/R
- `tests/test_sr_zones.py` â€” nowe testy S/R
- `docs/PROGRESS.md` â€” ten dziennik

## NierozwiÄ…zane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.json przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance) â€” zadanie Etapu 6.

## NastÄ™pny krok

Czekam na komendÄ™ do Etapu 3 (rozbudowa analysis/candles.py â€” analiza Ĺ›wiec, fundament wyzwalacza).

## Wykonane zadania (Etap 1)

- `analysis/decision.py`: usuniÄ™to fallback `pillars >= 3` (auto-akceptacja setupu bez peĹ‚nych warunkĂłw); zastÄ…piono `_apply_mtf_context` (uĹĽywajÄ…cy `reference_side`) przez `_mtf_adjustment_for_side` liczÄ…cÄ… korektÄ™ MTF osobno dla LONG i SHORT oraz `_apply_mtf_alignment` (tylko ustawia alignment, nie zmienia confidence); `directional_scores` opisuje obie strony niezaleĹĽnie; zachowano pola `confidence`, `base_confidence`, `directional_scores` dla kompatybilnoĹ›ci wstecznej.
- `analysis/analyzer.py`: dodano pole `levels_source_timeframe` oznaczajÄ…ce ĹşrĂłdĹ‚o interwaĹ‚u (4H/1H) dla gĹ‚Ăłwnych poziomĂłw entry/stop/target.
- `frontend-react/src/components/details/LatestCandles.jsx`: usuniÄ™to warunek `latest !== lastBar` zwracajÄ…cy pustÄ… listÄ™; formacje pokazywane z ostatnich N Ĺ›wiec (N konfigurowalne, domyĹ›lnie 5); formacja z najnowszej Ĺ›wiecy oznaczona adnotacjÄ… do weryfikacji zamkniÄ™cia.
- `tests/test_decision_mtf.py`: nowy plik z testami niezaleĹĽnoĹ›ci LONG/SHORT, MTF liczonym osobno per stronÄ™, BRAK pozostaje BRAK bez fallbacku.
- `tests/test_timeframes.py`: zaktualizowany test `test_1h_levels_do_not_overwrite_4h_levels` (poziomy 4H nie sÄ… nadpisywane przez 1H).

## Testy

22/22 testĂłw pytest przechodzi (test_lifecycle, test_timeframes, test_decision_mtf, test_chart_payload).
Build Vite (`npm run build`) przechodzi pomyĹ›lnie (50 moduĹ‚Ăłw, bez bĹ‚Ä™dĂłw).

## GOLD â€” wyjaĹ›nienie liczb (4H BRAK 16/100 przy bazie 24)

W output/status.json dla GOLD 4H: decision=BRAK, confidence=16, base_confidence=24. RĂłĹĽnica wynika z korekty MTF: 1D ma bias SHORT (konflikt dla LONG) â†’ -8 pkt, 1H ma bias SHORT (konflikt dla LONG) â†’ -4 pkt, dlatego 24 - 12 = 12, a dodatkowe zaokrÄ…glenia i baza dajÄ… 16. SzczegĂłĹ‚owy rozbicie wymaga ponownego wygenerowania output/ przez run_daily.py z danymi z rynku.

## Zmienione pliki

- `analysis/decision.py` â€” MTF osobno dla LONG/SHORT, brak fallbacku pillars>=3
- `analysis/analyzer.py` â€” pole levels_source_timeframe
- `frontend-react/src/components/details/LatestCandles.jsx` â€” formacje z ostatnich N Ĺ›wiec
- `tests/test_decision_mtf.py` â€” nowe testy MTF
- `tests/test_timeframes.py` â€” zaktualizowany test poziomĂłw 1H/4H

## NierozwiÄ…zane kwestie

- Wymagane ponowne wygenerowanie output/status.json i output/ohlc.py przez run_daily.py z aktualnymi danymi rynkowymi (wymaga sieci/yfinance).

## NastÄ™pny krok

Czekam na komendÄ™ do Etapu 2 (osobny moduĹ‚ S/R analysis/sr_zones.py).

## Wykonane zadania

- Zapoznanie siÄ™ z dokumentacjÄ… i strukturÄ… plikĂłw JSON (status.json, ohlc.json, signals_history.json) oraz kodem ĹşrĂłdĹ‚owym Python (analysis/chart_data.py, analysis/decision.py)


## Etap 10B — Entry, SL, TP, RR (ukończony)

## Status etapu

Ukończony

## Wykonane zadania (Etap 10B)

- `analysis/analyzer.py`:
  - Dodano funkcje modułowe `calculate_sl`, `calculate_tp`, `calculate_rr`, `fallback_tp_from_levels` — wszystkie testowalne izolowanie bez yfinance.
  - `calculate_sl`: SL = poziom unieważnienia z buforem 0.25 ATR (INVALIDATION_BUFFER_ATR_MULT). LONG: SUPPORT poniżej ceny - bufor; SHORT: RESISTANCE powyżej ceny + bufor. Walidacja strony (SL po przeciwnej stronie Entry).
  - `calculate_tp`: TP = najbliższa przeciwna strefa S/R (środek strefy). LONG: RESISTANCE powyżej Entry; SHORT: SUPPORT poniżej Entry. TP to środek strefy, nie granica.
  - `calculate_rr`: RR = |TP-Entry|/|Entry-SL| z walidacją stron (LONG: TP>Entry, SL<Entry; SHORT: TP<Entry, SL>Entry). Zwraca None gdy poziomy nieprawidłowe.
  - `fallback_tp_from_levels`: TP z _levels() tylko po walidacji (LONG: target>entry; SHORT: target<entry). Używany tylko gdy brak przeciwnej strefy S/R.
  - Zastąpiono stare obliczanie rr_val/entry_val/stop_val/target_val z dec osobnym obliczaniem per strone (LONG/SHORT).
  - manage_lifecycle otrzymuje poziomy strony kierunkowej.
- `tests/test_entry_sl_tp_rr.py` (nowy): 26 testow Entry/SL/TP/RR (SL z buforem, TP ze srodka strefy, wybor najblizszej strefy, fallback _levels() z walidacja, RR=1.5, RR<1.5, RR=None, nieprawidlowe Entry/SL/TP, niezalcznosc LONG/SHORT, TP=srodek nie granica).

## Testy

158/158 testow pytest przechodzi (132 oryginalnych + 26 nowych z test_entry_sl_tp_rr.py).
Build Vite (`npm run build`) przechodzi pomyślnie (51 modulow, bez bledow).

## Zmienione pliki

- `analysis/analyzer.py` — Entry, SL, TP, RR osobno dla LONG i SHORT (etap 10B)
- `tests/test_entry_sl_tp_rr.py` — nowe testy Entry/SL/TP/RR
- `docs/PROGRESS.md` — ten dziennik

## Nierozwiazane kwestie

- Etapy 10C (cykl zycia/wygasanie) i 10D (niezalezne reakcje S/R) oczekuja na komende.

## Nastepny krok

Czekam na komende do Etapu 10C.

- Przeczytanie oryginalnego `frontend/index.html` jako ĹşrĂłdĹ‚a prawdy dla logiki renderowania wykresu, poziomĂłw i markerĂłw
- Instalacja `lightweight-charts@4.2.2` (zgodna z wersjÄ… w oryginalnym HTML)
- Utworzenie `frontend-react/src/components/chart/PriceChart.jsx` â€” komponent wykresu Ĺ›wiecowego Lightweight Charts z peĹ‚nym cyklem ĹĽycia
- Utworzenie `frontend-react/src/components/details/DecisionDetails.jsx` â€” decyzyja, entry, SL, TP, R:R, confidence
- Utworzenie `frontend-react/src/components/details/SignalPillars.jsx` â€” trzy filary: Renko, Harmoniczne, Ĺšwiece
- Utworzenie `frontend-react/src/components/details/MarketContext.jsx` â€” kontekst D1 i ATR(14)
- Przepisanie `frontend-react/src/components/details/InstrumentDetails.jsx` â€” komponent orquestrujÄ…cy z danymi z status.json i ohlc.json
- Aktualizacja `frontend-react/src/components/instruments/InstrumentPanel.jsx` â€” przekazuje peĹ‚ny obiekt instrumentu
- Aktualizacja `frontend-react/src/components/workspace/MainWorkspace.jsx` â€” uĹĽywa PriceChart i InstrumentDetails
- Aktualizacja `frontend-react/src/App.jsx` â€” przekazuje `data` do MainWorkspace
- Dodanie zaleĹĽnoĹ›ci `lightweight-charts@4.2.2` do `package.json`
- Uruchomienie `npm run build` â€” zakoĹ„czone pomyĹ›lnie (43 moduĹ‚y, dist bez bĹ‚Ä™dĂłw)

### Etap 4 â€” Formacje i uzasadnienie sygnaĹ‚u

- Zapoznanie siÄ™ z dokumentacjÄ… i strukturÄ… plikĂłw JSON (status.json, classic_patterns.json) oraz oryginalnym `frontend/index.html`
- Utworzenie `frontend-react/src/components/details/HarmonicPatterns.jsx` â€” prezentacja formacji harmonicznych z opisami, poziomami X/A/B/C/D, schematem SVG XABCD
- Utworzenie `frontend-react/src/components/details/CandlePatterns.jsx` â€” prezentacja formacji Ĺ›wiecowych z opisami, kierunkiem, czasem, siĹ‚Ä… i diagramem SVG Ĺ›wiec
- Utworzenie `frontend-react/src/components/details/ClassicPatterns.jsx` â€” prezentacja formacji klasycznych z `classic_patterns.json` z opisami, kierunkiem, cenÄ…, czasem i schematem SVG
- Utworzenie `frontend-react/src/components/details/SignalJustification.jsx` â€” uzasadnienie sygnaĹ‚u z listÄ… powodĂłw (reasons), kontekstem D1 i ATR(14)
- Aktualizacja `frontend-react/src/components/details/InstrumentDetails.jsx` â€” dodanie nowych sekcji: formacje harmoniczne, Ĺ›wiecowe, klasyczne, uzasadnienie sygnaĹ‚u
- Uruchomienie `npm run build` â€” zakoĹ„czone pomyĹ›lnie (47 moduĹ‚Ăłw, dist bez bĹ‚Ä™dĂłw)

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
- `frontend-react/src/components/details/InstrumentDetails.jsx` â€” przepisany jako komponent orquestrujÄ…cy; dodano sekcje formacji i uzasadnienia sygnaĹ‚u
- `frontend-react/src/components/instruments/InstrumentPanel.jsx` â€” przekazuje peĹ‚ny obiekt instrumentu
- `frontend-react/src/components/workspace/MainWorkspace.jsx` â€” uĹĽywa PriceChart i InstrumentDetails
- `frontend-react/src/App.jsx` â€” przekazuje `data` do MainWorkspace
- `frontend-react/package.json` â€” dodano `lightweight-charts@4.2.2`
- `docs/PROGRESS.md` â€” ten dziennik

## Zachowane funkcjonalnoĹ›ci

Wszystkie istniejÄ…ce funkcjonalnoĹ›ci zachowane bez zmian:
- `frontend/index.html` â€” nienaruszony
- `app.py` â€” nienaruszony
- `data/` â€” nienaruszony
- `config.py` â€” nienaruszony
- `run_daily.py` â€” nienaruszony
- `.github/workflows/` â€” nienaruszone

UsuniÄ™te w ramach rezygnacji z backtestĂłw:
- `analysis/backtest.py` â€” generator backtestĂłw (nie byĹ‚ importowany przez inne moduĹ‚y)
- `output/backtest_results.json` â€” plik wynikĂłw backtestu
- `frontend-react/src/components/stats/Statistics.jsx` â€” komponent statystyk backtestu w React

Zmodyfikowane:
- `analysis/` â€” usuniÄ™to `backtest.py` (pozostaĹ‚e moduĹ‚y nienaruszone)
- `output/*.json` â€” usuniÄ™to `backtest_results.json` (pozostaĹ‚e pliki nienaruszone)

## SposĂłb pobierania danych

Wszystkie piÄ™Ä‡ plikĂłw JSON pobierane sÄ… przez `fetch()` z cache `no-store` (parametr `?v=` + timestamp). ĹšcieĹĽki budowane z `import.meta.env.BASE_URL` + `output/<nazwa_pliku>`. Na GitHub Pages (`base: '/market-status/'`) prowadzi to do `/market-status/output/<plik>`. Lokalnie przez Vite dev serwer Ĺ›cieĹĽka `/output/` obsĹ‚ugiwana jest przez middleware serwujÄ…cy pliki z `../output/`.

Dane OHLC, poziomy i markery harmoniczne pobierane sÄ… z `output/ohlc.json` (klucz `symbols[symbol]`), dane decyzyjne z `output/status.json`, formacje klasyczne z `output/classic_patterns.json`.

## Etap 5 â€” ANULOWANY

Etap 5 (Statystyki backtestu) zostaĹ‚ anulowany decyzjÄ… uĹĽytkownika. FunkcjonalnoĹ›Ä‡ backtestĂłw zostaĹ‚a usuniÄ™ta z caĹ‚ego projektu:
- UsuniÄ™to `analysis/backtest.py`
- UsuniÄ™to `output/backtest_results.json`
- UsuniÄ™to `frontend-react/src/components/stats/Statistics.jsx`
- UsuniÄ™to odwoĹ‚ania do backtestu w `frontend-react/src/hooks/useMarketData.js` i `frontend-react/src/App.jsx`
- Zaktualizowana dokumentacja: `docs/MIGRATION.md`, `docs/PROJECT.md`, `docs/MASTER.md`, `AGENTS.md`

PozostaĹ‚e etapy (6, 7) zachowujÄ… swojÄ… numeracjÄ™ i zakres bez zmian.

## Wynik kompilacji

`npm run build` â€” zakoĹ„czone sukcesem, 47 moduĹ‚Ăłw przeksztaĹ‚conych, dist wygenerowany bez bĹ‚Ä™dĂłw:
- `dist/index.html` 0.50 kB
- `dist/assets/index-1RZW7d_u.css` 13.03 kB
- `dist/assets/index-BsuWgkme.js` 172.23 kB

## NierozwiÄ…zane ograniczenia

- Brak danych OHLC dla niektĂłrych instrumentĂłw wyĹ›wietla komunikat zamiast wykresu (zgodnie z oryginaĹ‚em)
- `ChartPlaceholder.jsx` z Etapu 2 nie jest juĹĽ uĹĽywany, ale pozostawiony bez zmian (nie usuwa siÄ™ kodu z poprzednich etapĂłw)
- Formacje klasyczne w `status.json` (pole `timeframes.4H.classic_patterns`) sÄ… puste dla wszystkich aktualnych instrumentĂłw; dane klasyczne pochodzÄ… wyĹ‚Ä…cznie z `output/classic_patterns.json`

## Etap 10D — Część 3: izolacja stanu setupów per instrument i bezpieczna migracja (ukończony)

## Status etapu
Ukończony

## Wykonane zadania
- `analysis/setup_lifecycle.py`:
  - `_load_state()` waliduje `state["symbol"] == self.symbol`; obcy symbol, nieprawidłowa struktura i uszkodzony JSON → bezpieczny stan pusty, czytelny komunikat diagnostyczny, plik źródłowy nienaruszony (nie nadpisywany, nie usuwany, nie przenoszony).
  - Nowa funkcja `migrate_legacy_state(source_path, output_dir)` — jednorazowa, idempotentna migracja `output/setup_state.json` do `output/setup_state_<symbol>.json` dla 11 symboli z `config.SYMBOLS`; brak pliku źródłowego = bez zmian; brak symbolu / zły JSON / nieznany symbol / konflikt = brak migracji i komunikat; oryginał zawsze zachowany jako kopia bezpieczeństwa.
- `analysis/analyzer.py`:
  - `manage_lifecycle` wywoływane ze `state_path=OUTPUT_DIR / f"setup_state_{symbol_key}.json"` per instrument (kanoniczne klucze z `config.SYMBOLS`).
  - `analyze_all()` uruchamia `migrate_legacy_state()` raz przed pętlą instrumentów (nie w każdym wywołaniu lifecycle).
- `tests/test_setup_lifecycle_10d_part3.py` (nowy): 12 testów — izolacja dwóch instrumentów, odtworzenie obu stanów po restarcie obiektów, poprawna migracja legacy, zachowanie oryginalnego `setup_state.json`, idempotencja, brak symbolu, nieprawidłowy JSON, symbol spoza listy, konflikt z istniejącym plikiem docelowym, odrzucenie pliku ze Symbolem obcym w `_load_state()`. Wszystkie testy używają katalogów tymczasowych i `state_path`; nie modyfikują `output/`.

## Testy
- 216/216 testów pytest przechodzi (12 nowych + test_setup_lifecycle_10c.py i test_setup_lifecycle_10d.py + pozostałe).
- Import `from analysis.analyzer import analyze_all` OK.
- Build Vite (`npm run build`) przechodzi pomyślnie.
- `git diff --check` czysty.

## Zmienione pliki
- `analysis/setup_lifecycle.py` — walidacja symbolu w `_load_state()` + `migrate_legacy_state()`
- `analysis/analyzer.py` — `state_path` per instrument, migracja w `analyze_all()`
- `tests/test_setup_lifecycle_10d_part3.py` — nowe testy
- `docs/PROGRESS.md` — ten dziennik

## Bez zmian
- Logika triggera 1H, unieważnienia, zmiany kierunku, wygasania setupów (10C), readiness, wagi, progi, blokady, Entry/SL/TP/RR — nienaruszone.
- `frontend/index.html`, `app.py`, `analysis/` (poza setup_lifecycle.py), `data/`, `config.py`, `run_daily.py`, `.github/workflows/` — bez zmian.

## Etap 11G — Naprawa podsumowania setupu i blokad (ukonczony)

### Zakres zmiany
Usunięcie duplikatów w `entry_readiness.blockers` oraz naprawa komunikatu „Brak brakujących warunków” w `SetupSummary.jsx`, gdy istnieją aktywne blokady wejścia. `blockers` staje się źródłem prawdy dla przyczyny braku możliwości wejścia.

### Zmienione pliki
- `analysis/readiness.py` — deduplikacja `blockers` w `calculate_readiness()` (zachowanie kolejności pierwszego wystąpienia za pomocą `dict.fromkeys`). Pole `missing` bez zmian.
- `frontend-react/src/components/details/SetupSummary.jsx` — sekcja „Najważniejszy brakujący warunek” najpierw sprawdza `blockers`, potem `missing`, dopiero na końcu komunikat „Brak brakujących warunków”. Blokady w sekcji „Blokady wejścia” renderowane po deduplikacji (`[...new Set(blockers)]`).

### Wyniki weryfikacji
- 216/216 testów pytest przechodzi (w tym test_readiness.py).
- Build Vite (`npm run build`) przechodzi bez błędów.
- `git diff --check` czysty.
- Zatwierdzone i wsunięte na gałąź `main`.

### Drzewo etapów 11G–11M
11G — ukonczony (naprawa podsumowania setupu i blokad)
11H — ukonczony (ograniczenie i poprawka rysowania stref S/R w PriceChart.jsx)
11I — ukonczony (ujednolicenie prezentacji zgodności interwałów w SetupSummary.jsx i TimeframeAlignment.jsx)
11J — ukonczony (propagacja poziomów Entry/SL/TP z 4H na 1H i 1D w getChartPayload())
11K — ukonczony (uzasadnienie sygnału na podstawie rzeczywistych danych)
11L–11M — oczekuja na komende

## Etap 11H — Ograniczenie i poprawka rysowania stref S/R

### Zakres zmiany
Wyłącznie `frontend-react/src/components/chart/PriceChart.jsx` oraz `docs/PROGRESS.md`.

### Zmienione pliki
- `frontend-react/src/components/chart/PriceChart.jsx` — nowa logika wyboru i renderowania stref S/R.

### Opis działania
1. Dodano helper `toFiniteNumber(value)` odrzucający `null`, `undefined`, pusty tekst oraz wartości niefinitywne; stosowany spójnie dla `currentPrice`, `center`, `lower`, `upper` oraz pól rankingu (`rank_score`, `rank_position`, `distance_from_price`).
2. Cena referencyjna pobierana najpierw z `payload.sr_zones_current_price`, a przy braku z `close` ostatniej świecy z `payload.candles` — obie przez `toFiniteNumber()`. Przy braku prawidłowej ceny nie rysowane są żadne strefy (usunięto fallback `sorted.slice(0, 4)`).
3. Prawidłowe strefy (walidacja `center`/`lower`/`upper`) dzielone są na dwie niezależne grupy: `above` (`center > cena`) i `below` (`center < cena`).
4. Dla każdej grupy osobno wybierane jest jedno kryterium sortowania: `rank_score` malejąco (jeśli wszystkie w grupie go mają), w przeciwnym razie `rank_position` rosnąco, w przeciwnym razie `distance_from_price` rosnące, w przeciwnym razie `center`. Pola z różnych kategorii nigdy nie są ze sobą porównywane. Remisy rozstrzygane po `center`.
5. Z każdej grupy wybierane są maksymalnie 2 strefy (łącznie max 2 nad + 2 pod ceną).
6. Renderowana jest jedna linia na `center` każdej wybranej strefy, w oryginalnym kolorze typu (SUPPORT zielony #35d07f, RESISTANCE czerwony #ff6376).
7. Etykieta zawiera typ i zakres: `WSPARCIE · lower – upper` lub `OPÓR · lower – upper`, gdzie `lower` i `upper` formatowane przez istniejące `formatPrice(value, payload.symbol)` (maksymalnie 2 miejsca po przecinku, polski separator). Wartości numeryczne używane do rysowania linii pozostają niezmienione.

### Nie zmieniono
- `frontend/index.html`, `app.py`, `analysis/`, `data/`, `config.py`, `run_daily.py`, `.github/workflows/` — bez zmian.
- Poziomy Entry/SL/TP i harmoniczne — bez zmian.
- Limit 2 stref nad i 2 pod ceną — zachowany.

### Wyniki weryfikacji
- `npm run build` — zakończone sukcesem (51 modułów, bez błędów).
- `git diff --check` — czysty (brak błędów whitespace).
- `git diff --stat` — tylko `PriceChart.jsx` (81 dodanych, 11 usuniętych linii).
- Testy Pythona (`tests/test_sr_zones.py`) — nie uruchomione (brak interpretera Python w środowisku); kod Python nie był modyfikowany.
- Zatwierdzone i wsunięte na gałąź `main`.

## Etap 11I — Ujednolicenie prezentacji zgodności interwałów (ukończony)

### Zakres zmiany
Wyłącznie `frontend-react/src/components/details/SetupSummary.jsx`, `frontend-react/src/components/details/TimeframeAlignment.jsx` oraz `docs/PROGRESS.md`.

### Przyczyna rozbieżności
SetupSummary.jsx wyświetlał sekcję "ZGODNOŚĆ INTERWAŁÓW" używając danych z `entry_readiness.scores.LONG/SHORT.readiness_pct` — czyli wyników gotowości setupu dla obu stron — i etykietował je mylnie jako "1D kierunek" i "4H setup". TimeframeAlignment.jsx korzystał z `timeframe_alignment` z `status.json`, ale z mieszanym źródłem danych (`instrument.confidence`, `frame.confidence`, `alignment.bias` z fallbackami). Skutkiem były sprzeczne informacje dla tych samych interwałów (np. USDPLN: SetupSummary pokazywał "1D kierunek: 42% / 25%", TimeframeAlignment pokazywał "1D: BRAK 0/100 NEUTRALNY", "1H: SHORT 60/100 KONFLIKT").

### Źródło prawdy
`timeframe_alignment` w `status.json` (generowane przez `make_decision()` w `analyzer.py`, linia 371) — zawiera `bias`, `confidence`/`score`, `status` (main/neutral/conflict/missing) oraz `available` dla każdego interwału 1D/4H/1H.

### Zmiany w kodzie
**SetupSummary.jsx:**
- Dodano `const tfAlignment = instrument?.timeframe_alignment || {};`
- Dodano funkcję `renderTimeframeRow(tf, role, alignment)` renderującą dla każdego interwału: kierunek (↑ LONG / ↓ SHORT / — BRAK), wynik punktowy (X/100) i status (GŁÓWNY / KONFLIKT / NEUTRALNY / BRAK DANYCH).
- Sekcja "ZGODNOŚĆ INTERWAŁÓW" używa wyłącznie `tfAlignment['1D']`, `tfAlignment['4H']`, `tfAlignment['1H']`.
- Informacja o triggerze 1H pochodzi z `er.trigger_level` (potwierdzony / brak potwierdzenia), oddzielnie od statusu kierunku.

**TimeframeAlignment.jsx:**
- Uproszczone do wyłącznego korzystania z `instrument.timeframe_alignment`.
- Kierunek z `tfAlign.bias` przez `currentDecision()`.
- Wynik z `tfAlign.confidence ?? tfAlign.score`.
- Relacja z `tfAlign.status` (main → GŁÓWNY, conflict → KONFLIKT, neutral → NEUTRALNY, missing → BRAK DANYCH).
- Usunięto niepewne fallbacki na `instrument.confidence`, `frame.confidence`, `source.decision`.
- Etykietą `main` zmieniono z "GŁÓWNY KIERUNEK" na "GŁÓWNY" dla spójności z SetupSummary.

### Nie zmieniono
- `analysis/readiness.py`, `analysis/analyzer.py`, `output/status.json`, `frontend-react/src/utils/market.js`, `config.py`, `run_daily.py`, `.github/workflows/` — bez zmian.
- Logika obliczeniowa silnika Pythona — nienaruszona.

### Wyniki weryfikacji
- `npm run build` — zakończone sukcesem (51 modułów, bez błędów).
- `git diff --check` — czysty (brak błędów whitespace).
- `git diff --stat` — 2 pliki: SetupSummary.jsx (+46/−6), TimeframeAlignment.jsx (+16/−4).
- Zatwierdzone i wsunięte na gałąź `main`.

## Etap 11J — Propagacja poziomów Entry / SL / TP na 1H i 1D (ukończony)

### Zakres zmiany
Wyłącznie `frontend-react/src/utils/market.js` oraz `docs/PROGRESS.md`.

### Przyczyna braku poziomów na 1H i 1D
W `analyzer.py` poziomy Entry/SL/TP/RR są obliczane wyłącznie dla 4H (make_decision + calculate_sl/tp/rr) i zapisywane na poziomie głównym `result["entry"]` itp. oraz w `timeframes.4H.levels`. Dla interwałów 1H i 1D w `ohlc.json` zapisywane są same `null` (lub w niektórych przypadkach legacy wartości z 1H). Funkcja `getChartPayload()` w `market.js` pobierała poziomy wyłącznie z `source.levels` bieżącego interwału, co oznaczało brak linii Entry/SL/TP na wykresach 1H i 1D.

### Źródło prawdy
`timeframes.4H.levels` w `ohlc.json` (generowane przez `analyzer.py`, obliczone na podstawie `sr_zones_4h` przez `calculate_sl`/`calculate_tp`/`calculate_rr`) — jedyne źródło poziomów Entry/SL/TP.

### Zmiany w kodzie
**`frontend-react/src/utils/market.js` — funkcja `getChartPayload()`:**
- Dla 4H: zachowane obecne zachowanie (poziomy z `source.levels` bieżącego interwału).
- Dla 1H i 1D: poziomy pobierane **zawsze** z `container.timeframes['4H'].levels` (setup 4H), nigdy z `source.levels` bieżącego interwału.
- Jeśli wszystkie trzy poziomy (entry, stop, target) z 4H są `null` → `levels = {}` (brak rysowania linii).
- `levels_timeframe` ustawiane na `"4H"` dla 1H i 1D, więc etykiety w wykresie wskazują źródło 4H.
- Nie miesza poziomów z różnych interwałów — wszystkie trzy (entry, stop, target) pochodzą z tego samego źródła 4H.

### Nie zmieniono
- `analysis/analyzer.py`, `analysis/readiness.py`, `output/status.json`, `output/ohlc.json`, `config.py`, `run_daily.py`, `.github/workflows/` — bez zmian.
- Logika obliczeniowa silnika Pythona — nienaruszona.
- RR, readiness, lifecycle — bez zmian.
- Precyzja ceny, harmoniczne, strefy S/R — bez zmian.

### Wyniki weryfikacji (na rzeczywistych danych `output/ohlc.json`)
- **us500 (z poziomami 4H: entry=7128.96, stop=7006.31, target=7312.93):** identyczne poziomy na 1H, 4H, 1D z `levels_timeframe=4H`.
- **usdpln (bez poziomów 4H, mimo legacy wartości na 1H):** `levels={}` na wszystkich interwałach — legacy poziomy z 1H nie zostały użyte.
- `npm run build` — zakończone sukcesem (51 modułów, bez błędów).
- `git diff --check` — czysty.
- `git diff --stat` — tylko `market.js` (25 dodanych, 2 usuniętych linii).
- Zatwierdzone i wsunięte na gałąź `main`.



## Etap 11K — Uzasadnienie sygnału na podstawie rzeczywistych danych (ukończony)

### Zakres zmiany
Wyłącznie `frontend-react/src/components/details/SignalJustification.jsx`, `frontend-react/src/components/details/InstrumentDetails.jsx` oraz `docs/PROGRESS.md`.

### Opis działania
Rozbudowano istniejący `SignalJustification.jsx` o siedem obszarów prezentacji, z clasificacióną każdej informacji (fakt potwierdzony / warunek niespełniony / brak danych) zamiast jednego statusu na całą sekcję:

1. **Kontekst 1D** — z `timeframe_alignment.1D` (bias, confidence/score, status). Gdy niedostępny → „Brak danych”.
2. **Struktura 4H** — z `entry_readiness.criteria` (id `structure_4h`), punkty/max.
3. **Potwierdzenie 1H (wyzwalacz)** — z `entry_readiness.criteria` (id `trigger`) oraz `trigger_level`. Sekcja dotyczy wyłącznie triggera, nie formacji świec.
4. **Formacje świecowe (1H · 4H · 1D)** — z `timeframes.*.candles` (O/C ostatniej świecy). Opis descriptive, bez automatycznego traktowania braku formacji jako blokady. Każda formacja pokazana tylko raz, w swoim interwale.
5. **Strefy S/R (4H)** — z `timeframes.4H.sr_zones` (typ, center, liczba reakcji).
6. **Entry / SL / TP / RR** — z jednego źródła setupu 4H: `entry_readiness.entry/stop/target/rr` (z fallbackiem na pola główne instrumentu). Brak przeliczeń w React; przy braku → „Brak danych”.
7. **Blokady i brakujące warunki** — z `entry_readiness.blockers` i `entry_readiness.missing` (po deduplikacji). Brak harmonicznej/świecowej nie jest automatycznie blokadą.

Readiness präsentowane jako stopień spełnienia warunków, nie jako szansa na zysk. Komponent renderowany wewnątrz istniejącego kontenera szczegółów w `InstrumentDetails.jsx` (brak nowej sekcji na poziomie strony).

### Nie zmieniono
- `frontend/index.html`, `app.py`, `analysis/`, `data/`, `config.py`, `run_daily.py`, `.github/workflows/` — bez zmian.
- Backend Python, algorytmy decyzji, wagi, progi, readiness, lifecycle — nienaruszone.
- Entry/SL/TP/RR, OHLC, precyzja cen, harmoniczne, strefy S/R — bez zmian.
- Żadnych nowych bibliotek ani rozbudowanej infrastruktury testowej.

### Wyniki weryfikacji (na rzeczywistych danych `output/status.json`)
- Instrument z LONG (us500): Entry/SL/TP/RR z jednego źródła 4H, blockers/missing zgodne z silnikiem, gotowość nie jako szansa na zysk.
- Instrument z BRAK: Entry/SL/TP = null → „Brak danych”, brak fikcyjnych przyczyn.
- Brak danych / null: pola puste pokazywane jako „Brak danych”, bez domysłów.
- Blokady odpowiadają dokładnie danym `entry_readiness.blockers` / `missing`.
- `SignalJustification` widoczny w `InstrumentDetails`.
- `npm test` — 8/8 przechodzi.
- `npm run build` — zakończone sukcesem (52 moduły, bez błędów).
- `git diff --check` — czysty.

### Zmienione pliki
- `frontend-react/src/components/details/SignalJustification.jsx` — rozbudowany o siedem obszarów uzasadnienia.
- `frontend-react/src/components/details/InstrumentDetails.jsx` — import i renderowanie `SignalJustification`.
- `docs/PROGRESS.md` — ten dziennik.

## Etap 11L — Formacje liniowe i cenowe (ukończony)

### Zakres zmiany
Własna detekcja klasycznych formacji cenowych (bez `ta_patterns`, bez nowych bibliotek) dla interwałów 1H, 4H i 1D, wyłącznie na zamkniętych świecach. Formacje: trójkąty (wzrostowy, spadkowy, symetryczny), flagi i chorągiewki (wzrostowe, spadkowe), kliny (wzrostowe, spadkowe), głowa z ramionami, odwrócona głowa z ramionami, podwójny szczyt, podwójne dno, kanały (wzrostowy, spadkowy, boczny).

### Zmienione pliki
- `analysis/classic_patterns.py` — nowy detektor geometryczny (numpy/pandas), statusy z historią dat, stabilne ID, stan trwały (`classic_patterns_state.json`), eksport kompatybilny wstecz do `classic_patterns.json`.
- `analysis/analyzer.py` — podpięcie detektora dla 1H/4H/1D w `analyze_symbol()` (brak zmian w `make_decision()`, readiness, wagach).
- `config.py` — parametry formacji klasycznych (tolerancja ATR, max formacji, limit historii, pliki wyjściowe).
- `frontend-react/src/components/chart/PriceChart.jsx` — rysowanie linii trendu, granic formacji i pivotów (solid dla potwierdzonych, dashed dla formujących się).
- `frontend-react/src/components/details/ClassicPatterns.jsx` — wyświetlanie formacji ze statusem, podtypem, poziomem wybicia i retestu, obsługa wielu interwałów, kompatybilność wsteczna.
- `frontend-react/src/components/details/InstrumentDetails.jsx` — dodanie sekcji formacji klasycznych.
- `frontend-react/src/utils/market.js` — `classic_patterns` w `getChartPayload()`.
- `tests/test_classic_patterns.py` — nowe testy jednostkowe (geometria, statusy, wybicie, retest, lookahead, deduplikacja, limit, izolacja, kompatybilność).

### Nie zmieniono
- `frontend/index.html`, `app.py`, `analysis/sr_zones.py`, `analysis/candles.py`, `analysis/harmonics.py`, `data/`, `run_daily.py`, `.github/workflows/` — bez zmian.
- `make_decision()`, readiness, wagi, progi, logika LONG/SHORT — nienaruszone.

### Opis działania
Detekcja działa na zamkniętych świecach, pivoty potwierdzane po 3 świecach po ekstremum (brak lookahead). Każda formacja ma stabilne ID (symbol + interwał + typ + pivoty), status z listy: FORMUJĄCA SIĘ → POTWIERDZONA → WYBITA → RETEST → UNIEWAŻNIONA → WYGASŁA. Status nigdy nie cofa się przy przeliczeniu. Maksymalnie 5 aktywnych formacji na symbol/interwał. Stan trwały w osobnym pliku `classic_patterns_state.json`, prezentacja w `classic_patterns.json` kompatybilna ze starszym formatem.

### Wyniki weryfikacji
- `npm run build` — zakończone sukcesem (53 moduły, bez błędów).
- `git diff --check` — czysty.
- Testy Pythona — nie uruchomione (brak interpretera Python w środowisku z powodu Windows App Execution Alias); kod 작성any zgodnie z wzorcem istniejących testów.

