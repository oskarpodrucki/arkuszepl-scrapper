from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

ALLOWED_HOSTS = {"arkusze.pl", "www.arkusze.pl"}
FILE_EXTENSIONS = {".pdf", ".zip"}
MONTHS = (
    "styczen", "stycznia", "styczeń", "styczniu",
    "czerwiec", "czerwca", "czerwcu",
    "sierpien", "sierpnia", "sierpień", "sierpniu",
    "maj", "maja", "maju", "kwiecien", "kwietnia", "kwiecień",
    "marzec", "marca", "marcu", "luty", "lutego", "lutym",
    "listopad", "listopada", "listopadzie",
    "pazdziernik", "październik", "wrzesien", "września",
    "poprawkowa", "poprawkowy", "probna", "próbna",
)
YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
BAD_FOLDER_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (compatible; EducationalArchiveDownloader/1.0; "
        "+https://arkusze.pl/)"
    )
})


def safe_name(value: str, max_len: int = 140) -> str:
    value = unquote(value).strip()
    value = BAD_FOLDER_CHARS.sub("_", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .-_")
    return (value or "bez-nazwy")[:max_len].rstrip(" .")


def normalize_url(url: str) -> str:
    url, _fragment = urldefrag(url.strip())
    return url


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in ALLOWED_HOSTS


def fetch_page(url: str, timeout: int = 30) -> tuple[str, BeautifulSoup] | None:
    try:
        response = SESSION.get(url, timeout=timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and not response.text.lstrip().lower().startswith(
            ("<!doctype html", "<html")
        ):
            print(f"  [POMINIĘTO] To nie wygląda na stronę HTML: {url}")
            return None
        response.encoding = response.apparent_encoding or response.encoding
        return response.url, BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as exc:
        print(f"  [BŁĄD STRONY] {url} — {exc}")
        return None


def is_file_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return Path(path).suffix in FILE_EXTENSIONS


def is_probable_exam_page(url: str, link_text: str, category_url: str) -> bool:
    """Conservative filter: identify dated exam pages, not general site navigation."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    category_path = urlparse(category_url).path.strip("/")
    if not path or path == category_path or is_file_url(url):
        return False
    if not is_allowed_url(url):
        return False

    slug = path.rsplit("/", 1)[-1].lower()
    text = f"{slug} {link_text.lower()}"
    has_year = bool(YEAR_RE.search(text))
    has_exam_term = any(word in text for word in (
        "egzamin", "matura", "arkusz", "inf-04", "inf04", "poziom-podstawowy",
        "poziom-rozszerzony", "ósmoklas", "osmoklas", "kwalifikacja",
    ))
    has_session = any(month in text for month in MONTHS) or any(
        word in text for word in ("zima", "lato", "sesja", "termin")
    )
    # Most exam pages have a year; the extra clues help catch pages whose link text
    # contains a date even if the slug does not.
    return has_year and has_exam_term and (has_session or "egzamin" in text or "matura" in text)


def discover_exam_pages(category_url: str, delay: float) -> list[tuple[str, str]]:
    print(f"\n[KATEGORIA] {category_url}")
    fetched = fetch_page(category_url)
    if not fetched:
        return []
    final_url, soup = fetched

    found: dict[str, str] = {}
    for anchor in soup.select("a[href]"):
        href = normalize_url(urljoin(final_url, anchor.get("href", "")))
        text = anchor.get_text(" ", strip=True)
        if not is_allowed_url(href) or is_file_url(href):
            continue
        if is_probable_exam_page(href, text, final_url):
            found.setdefault(href, text or urlparse(href).path.rsplit("/", 1)[-1])

    # Follow only obvious category pagination links, not arbitrary site links.
    # This helps when older exams are split across multiple category pages.
    pagination_urls: list[str] = []
    for anchor in soup.select("a[href]"):
        href = normalize_url(urljoin(final_url, anchor.get("href", "")))
        text = anchor.get_text(" ", strip=True).lower()
        rel = " ".join(anchor.get("rel", [])).lower()
        if not is_allowed_url(href) or is_file_url(href):
            continue
        if href == final_url:
            continue
        if "next" in rel or text in {"następna", "następne", "dalej", "»", "›", "→"}:
            pagination_urls.append(href)
        elif re.search(r"/page/\d+/?$", urlparse(href).path):
            pagination_urls.append(href)

    seen_pages = {final_url}
    while pagination_urls:
        page_url = pagination_urls.pop(0)
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        time.sleep(delay)
        page_result = fetch_page(page_url)
        if not page_result:
            continue
        page_final, page_soup = page_result
        for anchor in page_soup.select("a[href]"):
            href = normalize_url(urljoin(page_final, anchor.get("href", "")))
            text = anchor.get_text(" ", strip=True)
            if is_probable_exam_page(href, text, final_url):
                found.setdefault(href, text or urlparse(href).path.rsplit("/", 1)[-1])
        for anchor in page_soup.select("a[href]"):
            href = normalize_url(urljoin(page_final, anchor.get("href", "")))
            text = anchor.get_text(" ", strip=True).lower()
            rel = " ".join(anchor.get("rel", [])).lower()
            if not is_allowed_url(href) or href in seen_pages:
                continue
            if "next" in rel or text in {"następna", "następne", "dalej", "»", "›", "→"}:
                pagination_urls.append(href)
            elif re.search(r"/page/\d+/?$", urlparse(href).path):
                pagination_urls.append(href)

    print(f"  Znalezione strony egzaminów: {len(found)}")
    return sorted(found.items(), key=lambda item: item[0])


def collect_downloads(exam_url: str) -> list[tuple[str, str]]:
    fetched = fetch_page(exam_url)
    if not fetched:
        return []
    final_url, soup = fetched
    links: dict[str, str] = {}
    for anchor in soup.select("a[href]"):
        href = normalize_url(urljoin(final_url, anchor.get("href", "")))
        if not is_allowed_url(href) or not is_file_url(href):
            continue
        label = anchor.get_text(" ", strip=True)
        links.setdefault(href, label or Path(urlparse(href).path).name)
    return sorted(links.items())


def download_file(url: str, destination: Path, timeout: int = 90) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return "skipped_exists"

    temp_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with SESSION.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" in content_type:
                raise ValueError(f"Serwer zwrócił HTML zamiast pliku ({content_type})")
            with temp_path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        output.write(chunk)

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            raise ValueError("Pobrany plik jest pusty")

        # Basic format check to avoid saving an error page as a PDF/ZIP.
        with temp_path.open("rb") as file:
            header = file.read(8)
        suffix = destination.suffix.lower()
        if suffix == ".pdf" and not header.startswith(b"%PDF-"):
            raise ValueError("Plik ma rozszerzenie PDF, ale nie ma nagłówka PDF")
        if suffix == ".zip" and not (
            header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06")
            or header.startswith(b"PK\x07\x08")
        ):
            raise ValueError("Plik ma rozszerzenie ZIP, ale nie ma nagłówka ZIP")

        temp_path.replace(destination)
        return "downloaded"
    except (requests.RequestException, OSError, ValueError) as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(str(exc)) from exc


def run(urls: list[str], output_root: Path, delay: float) -> int:
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "raport_pobierania.csv"
    report_rows: list[dict[str, str]] = []
    seen_exam_urls: set[str] = set()
    total_downloads = 0
    total_failures = 0

    for category_url in urls:
        category_url = normalize_url(category_url)
        if not is_allowed_url(category_url):
            print(f"[BŁĄD] Dozwolone są wyłącznie adresy arkusze.pl: {category_url}")
            total_failures += 1
            continue

        exam_pages = discover_exam_pages(category_url, delay)
        if not exam_pages:
            print("  [UWAGA] Nie znaleziono stron egzaminów. Sprawdź, czy URL prowadzi do kategorii.")
        for exam_url, link_text in exam_pages:
            if exam_url in seen_exam_urls:
                continue
            seen_exam_urls.add(exam_url)

            slug = urlparse(exam_url).path.strip("/").rsplit("/", 1)[-1]
            folder_name = safe_name(slug)
            exam_folder = output_root / folder_name
            print(f"\n[EGZAMIN] {link_text}\n  {exam_url}")

            downloads = collect_downloads(exam_url)
            if not downloads:
                print("  [UWAGA] Nie znaleziono linków PDF/ZIP.")
                report_rows.append({
                    "egzamin": exam_url, "plik": "", "url_pliku": "",
                    "status": "no_files_found", "szczegoly": "",
                })
                time.sleep(delay)
                continue

            print(f"  Pliki do sprawdzenia: {len(downloads)}")
            used_names: set[str] = set()
            for file_url, label in downloads:
                raw_name = Path(urlparse(file_url).path).name or "plik"
                filename = safe_name(raw_name)
                # Avoid collisions if two different URLs use the same filename.
                if filename in used_names:
                    stem, suffix = Path(filename).stem, Path(filename).suffix
                    filename = f"{stem}_{abs(hash(file_url)) % 100000:05d}{suffix}"
                used_names.add(filename)
                destination = exam_folder / filename
                try:
                    status = download_file(file_url, destination)
                    if status == "downloaded":
                        total_downloads += 1
                        print(f"    [POBRANO] {filename}")
                    else:
                        print(f"    [POMINIĘTO] {filename} — już istnieje")
                    details = label
                except RuntimeError as exc:
                    total_failures += 1
                    status = "failed"
                    details = str(exc)
                    print(f"    [BŁĄD] {filename} — {details}")
                report_rows.append({
                    "egzamin": exam_url,
                    "plik": str(destination.relative_to(output_root)),
                    "url_pliku": file_url,
                    "status": status,
                    "szczegoly": details,
                })
                time.sleep(delay)
            time.sleep(delay)

    with report_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["egzamin", "plik", "url_pliku", "status", "szczegoly"],
        )
        writer.writeheader()
        writer.writerows(report_rows)

    print("\n========== PODSUMOWANIE ==========")
    print(f"Nowo pobrane pliki: {total_downloads}")
    print(f"Błędy: {total_failures}")
    print(f"Raport: {report_path.resolve()}")
    print(f"Katalog docelowy: {output_root.resolve()}")
    return 1 if total_failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Masowe pobieranie PDF/ZIP z kategorii serwisu arkusze.pl."
    )
    parser.add_argument(
        "--url", action="append", dest="urls",
        help="URL kategorii; można podać wiele razy. Jeśli pominięty, program zapyta o linki.",
    )
    parser.add_argument(
        "--output", default="pobrane_arkusze",
        help="Katalog docelowy (domyślnie: ./pobrane_arkusze).",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Przerwa w sekundach między żądaniami (domyślnie: 1.0). Nie ustawiaj 0 bez potrzeby.",
    )
    args = parser.parse_args()

    urls = args.urls or []
    if not urls:
        print("Wklej URL kategorii arkusze.pl. Pusty wiersz kończy listę.")
        while True:
            try:
                value = input("URL> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not value:
                break
            urls.append(value)

    if not urls:
        print("Nie podano żadnego URL.")
        return 2
    if args.delay < 0:
        print("--delay nie może być ujemny.")
        return 2

    try:
        return run(urls, Path(args.output), args.delay)
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika. Uruchom ponownie, aby kontynuować.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
