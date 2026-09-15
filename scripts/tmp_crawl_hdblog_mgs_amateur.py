from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://hdblog.me/category/mgs-amateur/"
OUTPUT = Path("hdblog_mgs_amateur.json")
MAX_PAGES = 500
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)

NUMBER_RE = re.compile(r"\b(?:\d{2,4})?[A-Za-z][A-Za-z0-9]{1,15}(?:[-_][A-Za-z0-9]{1,15})+\b")
FINAL_NUMERIC_SUFFIX_RE = re.compile(r"[-_]\d+[A-Za-z]?$", re.IGNORECASE)


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
        },
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise
            last_error = exc
        except Exception as exc:  # pragma: no cover - temporary network helper
            last_error = exc
        time.sleep(2**attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def visible_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<script\b.*?</script>", " ", raw_html)
    text = re.sub(r"(?is)<style\b.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def extract_numbers(raw_html: str) -> set[str]:
    text = visible_text(raw_html)
    numbers: set[str] = set()

    # Primary signal used by HDblog product posts.
    for marker in re.finditer(r"品番\s*[:：]?", text, re.IGNORECASE):
        chunk = text[marker.end() : marker.end() + 100]
        match = NUMBER_RE.search(chunk)
        if match:
            numbers.add(match.group(0).upper().replace("_", "-"))

    # Backup: titles/slugs in this category usually begin with the product number.
    for match in NUMBER_RE.finditer(text):
        value = match.group(0).upper().replace("_", "-")
        if re.search(r"\d", value) and FINAL_NUMERIC_SUFFIX_RE.search(value):
            numbers.add(value)

    return numbers


def number_family(number: str) -> str:
    normalized = number.upper().replace("_", "-").strip("- ")
    return FINAL_NUMERIC_SUFFIX_RE.sub("", normalized).strip("-")


def main() -> None:
    all_numbers: set[str] = set()
    pages_fetched = 0
    empty_streak = 0

    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"
        try:
            raw = fetch(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and page > 1:
                print(f"STOP_404_PAGE={page}")
                break
            raise

        lowered = raw.lower()
        if "just a moment" in lowered and "cloudflare" in lowered:
            raise RuntimeError(f"Cloudflare challenge on page {page}")

        page_numbers = extract_numbers(raw)
        pages_fetched = page
        before = len(all_numbers)
        all_numbers.update(page_numbers)
        added = len(all_numbers) - before
        print(f"PAGE={page} PAGE_NUMBERS={len(page_numbers)} NEW={added} TOTAL={len(all_numbers)}")

        if page_numbers:
            empty_streak = 0
        else:
            empty_streak += 1
            if page > 5 and empty_streak >= 3:
                print(f"STOP_EMPTY_STREAK_PAGE={page}")
                break

    families = sorted({number_family(number) for number in all_numbers if number_family(number)})
    numbers = sorted(all_numbers)
    payload = {
        "source": BASE_URL,
        "pages_fetched": pages_fetched,
        "numbers_count": len(numbers),
        "families_count": len(families),
        "families": families,
        "numbers": numbers,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"SUMMARY pages={pages_fetched} numbers={len(numbers)} families={len(families)}")
    print("FAMILIES_JSON=" + json.dumps(families, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
