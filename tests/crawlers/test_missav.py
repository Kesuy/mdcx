from pathlib import Path

import pytest
from parsel import Selector

from mdcx.crawlers.missav import MissavCrawler


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("MIDV-999-U", "midv-999"),
        ("MIDV-0999-UC", "midv-999"),
        ("MIDV999U", "midv-999"),
        ("010101-123-U", "010101-123"),
        ("100225_100", "100225-100"),
        ("10musume_031426_01", "031426-01"),
        ("caribbeancom-031426-001", "031426-001"),
    ],
)
def test_normalize_number_for_uncensored_judge(number: str, expected: str):
    assert MissavCrawler._normalize_number_for_uncensored_judge(number) == expected


@pytest.mark.parametrize(
    ("number", "mosaic", "expected"),
    [
        ("MIDV-999-U", "无码破解", False),
        ("MIDV-999-UC", "无码", False),
        ("MIDV-999", "无码", False),
        ("HEYZO-1234-U", "有码", True),
        ("010101-123-U", "有码", True),
        ("100225_100", "有码", True),
        ("10musume_031426_01", "有码", True),
        ("caribbeancom-031426-001", "有码", True),
    ],
)
def test_should_use_uncensored_search_by_original_number(number: str, mosaic: str, expected: bool):
    assert MissavCrawler._should_use_uncensored_search(number, mosaic) is expected


def test_is_soft_404_page_detects_not_found_template():
    html = Selector(
        text="""
        <html>
            <head>
                <meta property="og:title" content="MissAV | 免費高清AV在線看" />
                <meta property="og:image" content="https://missav.ws/missav/logo-square.png" />
                <title>MissAV | 免費高清AV在線看</title>
            </head>
            <body>
                <p>404</p>
                <h1>找不到頁面</h1>
            </body>
        </html>
        """
    )

    assert MissavCrawler._is_soft_404_page(html) is True


def test_is_soft_404_page_ignores_normal_detail_page():
    html = Selector(
        text="""
        <html>
            <head>
                <meta property="og:title" content="SNOS-004 絶頂快感 - MissAV" />
                <meta property="og:image" content="https://fourhoi.com/snos-004/cover-n.jpg" />
                <title>SNOS-004 絶頂快感 - MissAV</title>
            </head>
            <body>
                <h1>SNOS-004 絶頂快感</h1>
                <p>發行日期：2024-01-01</p>
            </body>
        </html>
        """
    )

    assert MissavCrawler._is_soft_404_page(html) is False


def test_numeric_search_prefers_maker_entry_from_duplicate_results():
    page = Path(__file__).parents[1] / "fixtures" / "missav" / "duplicate_numeric_search.html"
    crawler = MissavCrawler(client=None)
    assert (
        crawler._extract_first_detail_url_from_search(Selector(text=page.read_text(encoding="utf-8")), "010326-001")
        == "https://missav.ws/dm325/caribbeancom-010326-001/cn"
    )


@pytest.mark.parametrize(
    "alternative",
    ["caribbeancom-010326-0010", "caribbeancom-010327-001", "unrelated-010326-001"],
)
def test_numeric_search_does_not_promote_unrelated_or_partial_codes(alternative):
    crawler = MissavCrawler(client=None)
    page = Selector(text=f'<a href="/010326-001">Match</a><a href="/{alternative}">Other</a>')
    assert crawler._extract_first_detail_url_from_search(page, "010326-001") == "https://missav.ws/010326-001/cn"


@pytest.mark.parametrize("reverse", [True, False])
def test_numeric_search_priority_is_independent_of_result_position(reverse):
    crawler = MissavCrawler(client=None)
    paths = ["/010326_001", "/caribbeancom-010326_001"]
    if reverse:
        paths.reverse()
    page = Selector(text="".join(f'<a href="{path}">Result</a>' for path in paths))
    assert crawler._extract_first_detail_url_from_search(page, "010326-001") == (
        "https://missav.ws/caribbeancom-010326_001/cn"
    )


def test_explicit_maker_search_preserves_requested_maker():
    crawler = MissavCrawler(client=None)
    page = Selector(
        text=('<a href="/1pondo-010326-001">Other maker</a><a href="/caribbeancom-010326-001">Requested maker</a>')
    )
    assert crawler._extract_first_detail_url_from_search(page, "caribbeancom-010326-001") == (
        "https://missav.ws/caribbeancom-010326-001/cn"
    )
