# Arkusze.pl Scrapper

**Polski**

Narzędzie CLI do pobierania materiałów egzaminacyjnych z serwisu [arkusze.pl](https://arkusze.pl/). Podajesz adres strony kategorii, a program znajduje strony poszczególnych egzaminów i pobrać podlinkowane pliki PDF oraz ZIP.

> **Uwaga:** to niezależny projekt społecznościowy. Nie jest powiązany z arkusze.pl ani przez ten serwis zatwierdzony. Skuteczność wykrywania zależy od aktualnej struktury stron. Program nie gwarantuje znalezienia wszystkich egzaminów ani plików.

## Funkcje

- Znajdywanie stron egzaminów na podstawie strony kategorii.
- Pobieranie plików PDF i ZIP podlinkowanych na stronie egzaminu.
- Tworzenie oddzielnego katalogu dla każdego egzaminu.
- Wznawianie pracy przez pomijanie istniejących, niepustych plików.
- Podstawowa walidacja nagłówków PDF/ZIP.
- Prosty raport CSV z adresami, statusem i szczegółami błędów.
- Możliwość podania wielu kategorii w jednym uruchomieniu.

## Wymagania

- Python 3.10 lub nowszy
- Dostęp do internetu
- Zależności: `requests`, `beautifulsoup4`

## Instalacja

### Windows (PowerShell)

```powershell
git clone https://github.com/oskarpodrucki/arkuszepl-scrapper.git
cd arkusze-downloader
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jeśli PowerShell blokuje aktywację środowiska, możesz uruchomić program bez aktywacji, używając `.venv\Scripts\python.exe`.

### Linux / macOS

```bash
git clone https://github.com/oskarpodrucki/arkuszepl-scrapper.git
cd arkusze-downloader
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Użycie

### Tryb interaktywny

```bash
python main.py
```

Wklej adresy kategorii, po jednym na linię. Pusty wiersz kończy wprowadzanie i rozpoczyna pobieranie.

Przykładowe kategorie:

```text
URL> https://arkusze.pl/egzamin-zawodowy-kwalifikacja-inf-04/
URL> https://arkusze.pl/jezyk-polski-matura-poziom-podstawowy/
URL> https://arkusze.pl/matematyka-matura-poziom-podstawowy/
URL> https://arkusze.pl/jezyk-angielski-matura-poziom-podstawowy/
URL> 
```

### Jeden adres

```bash
python arkusze_downloader.py \
  --url "https://arkusze.pl/egzamin-zawodowy-kwalifikacja-inf-04/"
```

### Wiele adresów i własny katalog wyjściowy

```bash
python arkusze_downloader.py \
  --url "https://arkusze.pl/egzamin-zawodowy-kwalifikacja-inf-04/" \
  --url "https://arkusze.pl/matematyka-matura-poziom-podstawowy/" \
  --output "./moje-arkusze"
```

### Ustawienie przerwy między żądaniami

Domyślnie program robi przerwy między żądaniami, aby nie obciążać serwisu zbyt intensywnym ruchem. Możesz ustawić dłuższą przerwę:

```bash
python arkusze_downloader.py --url "https://arkusze.pl/egzamin-zawodowy-kwalifikacja-inf-04/" --delay 2
```

Nie ustawiaj bardzo krótkich przerw ani nie uruchamiaj wielu instancji równocześnie.

## Struktura wyników

```text
pobrane_arkusze/
├── raport_pobierania.csv
├── egzamin-zawodowy-inf-04-2026-czerwiec/
│   ├── ...pdf
│   └── ...zip
└── kolejny-egzamin/
    └── ...pdf
```

Nazwy folderów pochodzą z adresów stron egzaminów. Konkretna liczba i nazwy plików zależą od materiałów dostępnych na stronie.

## Raport CSV

Raport `raport_pobierania.csv` zawiera:

- `egzamin` — URL strony egzaminu,
- `plik` — ścieżkę lokalnego pliku,
- `url_pliku` — URL źródłowy,
- `status` — m.in. `downloaded`, `skipped_exists`, `failed` lub `no_files_found`,
- `szczegoly` — etykietę linku albo informację o błędzie.

Raport jest zapisywany w katalogu wyjściowym i otwiera się w arkuszach kalkulacyjnych.

## Jak działa wykrywanie

1. Program pobiera stronę kategorii.
2. Wyszukuje linki, których adresy lub etykiety wyglądają na strony egzaminów.
3. Otwiera każdą wykrytą stronę egzaminu.
4. Zbiera bezpośrednie linki do plików PDF i ZIP.
5. Pobiera pliki i zapisuje wynik w raporcie.

To heurystyczne wykrywanie, a nie pełny crawler całego serwisu. Jeśli kategoria korzysta z niestandardowej paginacji, ładowania JavaScript albo linki nie pasują do reguł, część materiałów może zostać pominięta. Po pierwszym uruchomieniu porównaj liczbę znalezionych egzaminów z tym, co widzisz w przeglądarce.

## Rozwiązywanie problemów

**`python` nie jest rozpoznawany**

- Windows: spróbuj `py --version`.
- Linux/macOS: spróbuj `python3 --version`.

**Nie znaleziono stron egzaminów**

- Upewnij się, że podałeś stronę kategorii, a nie pojedynczy PDF.
- Otwórz adres w przeglądarce i sprawdź, czy strona jest dostępna.
- Struktura serwisu mogła się zmienić; zgłoś problem wraz z adresem kategorii.

**Część plików nie została pobrana**

- Sprawdź `raport_pobierania.csv`.
- Uruchom ponownie program — poprawnie pobrane pliki zostaną pominięte.
- Niektóre pliki mogą być chwilowo niedostępne albo chronione przez serwis.

**Brakuje starszych egzaminów**

- Obecna wersja nie gwarantuje pełnego wykrycia archiwum. Zgłoś przykład brakującej strony, aby można było rozszerzyć parser.

## Odpowiedzialne korzystanie

- Korzystaj z umiarkowanego tempa pobierania.
- Przed użyciem sprawdź regulamin serwisu oraz warunki dotyczące pobierania i dalszego udostępniania materiałów.
- Nie publikuj pobranych arkuszy w tym repozytorium bez upewnienia się, że masz do tego prawa.
- To narzędzie pobiera wyłącznie pliki podlinkowane na obsługiwanych stronach; nie omija logowania, paywalli ani innych zabezpieczeń.
- Użytkownik odpowiada za przestrzeganie prawa, warunków serwisu i praw osób trzecich.

## Współtworzenie

Zgłoszenia błędów i propozycje zmian są mile widziane. W zgłoszeniu podaj:
1. URL kategorii lub egzaminu,
2. system operacyjny i wersję Pythona,
3. polecenie, które uruchomiłeś,
4. odpowiedni fragment logu (bez prywatnych danych).

Nie dołączaj pobranych materiałów, jeśli nie masz prawa ich redystrybuować.

## Licencja

Projekt jest udostępniany na licencji MIT. Zobacz [LICENSE](LICENSE).

Licencja dotyczy kodu tego repozytorium, a nie arkuszy, PDF-ów ani innych materiałów pobieranych ze stron zewnętrznych.
