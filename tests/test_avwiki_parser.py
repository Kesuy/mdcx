import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcx.config.manager import manager
from mdcx.core import avwiki, translate
from mdcx.core.avwiki import (
    _avwiki_number_variants,
    _numbers_match,
    get_actorname,
    parse_avwiki_actor_search,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "avwiki"
SEARCH_FIXTURE = FIXTURE_DIR / "search_300MIUM-1431.html"
CONTEXT_FIXTURE = FIXTURE_DIR / "context_300MIUM-1431.html"


def test_avwiki_parser_handles_extra_and_reordered_classes():
    html = SEARCH_FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "300MIUM-1431")

    assert actor == "善場まみ"
    assert candidates
    assert candidates[0][0] == "300MIUM-1431"
    assert candidates[0][1] == actor


def test_avwiki_parser_preserves_suffix_number_matching():
    html = SEARCH_FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "MIUM-1431")

    assert actor == "善場まみ"
    assert candidates[0][0] == "300MIUM-1431"


def test_avwiki_parser_falls_back_to_number_and_actor_link_context():
    html = CONTEXT_FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "300MIUM-1431")

    assert actor == "善場まみ"
    assert candidates == [("300MIUM-1431", "善場まみ")]


@pytest.mark.parametrize(
    ("number", "maker_number"),
    [
        ("821SBTH-005", "SBTH-005"),
        ("583ERKR-1032", "ERKR-1032"),
        ("766ESDX-046", "ESDX-046"),
        ("420ERK-085", "ERK-085"),
        ("420HOI-304", "HOI-304"),
        ("420HPT-034", "HPT-034"),
        ("435MFC-277", "MFC-277"),
    ],
)
def test_avwiki_prefixed_amateur_numbers_add_maker_number_fallback(number: str, maker_number: str):
    assert _avwiki_number_variants(number) == [number, maker_number]
    assert _numbers_match(number, maker_number)
    assert _numbers_match(maker_number, number)


def test_avwiki_number_fallback_does_not_strip_unrelated_numbers():
    assert _avwiki_number_variants("MFCS-164") == ["MFCS-164"]
    assert _avwiki_number_variants("HEYZO-1234") == ["HEYZO-1234"]
    assert not _numbers_match("ABC-123", "BC-123")


def test_avwiki_parser_matches_short_maker_number_to_prefixed_request():
    html = """
    <html><body><article><header>
      <ul class="post-meta clearfix">
        <li class="actress-name"><a href="/av-actress/real-name/">真实演员</a></li>
        <li>ERK-085</li>
      </ul>
    </header></article></body></html>
    """

    actor, candidates = parse_avwiki_actor_search(html, "420ERK-085")

    assert actor == "真实演员"
    assert candidates == [("ERK-085", "真实演员")]


def test_avwiki_lookup_retries_search_with_short_maker_number(monkeypatch):
    no_result_html = "<html><body><main>no result</main></body></html>"
    matched_html = """
    <html><body><article><header>
      <ul class="post-meta clearfix">
        <li class="actress-name"><a href="/av-actress/real-name/">真实演员</a></li>
        <li>ERK-085</li>
      </ul>
    </header></article></body></html>
    """

    class FakeClient:
        def __init__(self):
            self.urls = []

        async def get_text(self, url):
            self.urls.append(url)
            if url == "https://av-wiki.net/?s=420ERK-085":
                return no_result_html, ""
            if url == "https://av-wiki.net/?s=ERK-085":
                return matched_html, ""
            raise AssertionError(f"unexpected AV-Wiki request: {url}")

    client = FakeClient()

    class FakeLease:
        async def __aenter__(self):
            return SimpleNamespace(async_client=client)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(manager, "acquire_computed", lambda: FakeLease())

    success, actor = asyncio.run(get_actorname("420ERK-085"))

    assert success
    assert actor == "真实演员"
    assert client.urls == [
        "https://av-wiki.net/?s=420ERK-085",
        "https://av-wiki.net/?s=ERK-085",
    ]


def test_translate_uses_the_new_avwiki_lookup():
    assert translate.get_actorname is avwiki.get_actorname
