from pathlib import Path

import pytest
from parsel import Selector

from mdcx.crawlers.base import Context, CralwerException
from mdcx.crawlers.javdb_new import JavdbCrawler
from mdcx.models.types import CrawlerInput


@pytest.mark.asyncio
@pytest.mark.parametrize("page", ["search", "detail"])
async def test_login_required_page_reports_cookie_requirement(page):
    html = Selector((Path(__file__).parents[1] / "fixtures/javdb/login_required.html").read_text(encoding="utf-8"))
    crawler = JavdbCrawler(client=None)
    ctx = Context(input=CrawlerInput.empty())
    parse = crawler._parse_search_page if page == "search" else crawler._parse_detail_page

    with pytest.raises(CralwerException, match="JavDB Cookie"):
        await parse(ctx, html, "https://javdb.com/v/mOPegv")


@pytest.mark.asyncio
async def test_public_detail_with_login_link_still_parses_actors():
    html = Selector("""
        <a href="/login">登入</a>
        <h2 class="title is-4"><strong class="current-title">Sample</strong></h2>
        <span><a href="/actors/example">演员A</a><strong class="female">♀</strong></span>
    """)
    crawler = JavdbCrawler(client=None)
    ctx = Context(input=CrawlerInput.empty())

    data = await crawler._parse_detail_page(ctx, html, "https://javdb.com/v/example")

    assert data.title == "Sample"
    assert data.actors == ["演员A"]
