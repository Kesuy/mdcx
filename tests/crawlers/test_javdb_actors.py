from pathlib import Path

import pytest
from parsel import Selector

from mdcx.crawlers.base import Context
from mdcx.crawlers.javdb_new import JavdbCrawler, Parser
from mdcx.models.types import CrawlerInput


@pytest.mark.asyncio
async def test_uncensored_detail_extracts_actors_from_link_classes():
    html = Selector((Path(__file__).parents[1] / "fixtures/javdb/uncensored_actors.html").read_text(encoding="utf-8"))
    ctx = Context(input=CrawlerInput.empty())
    ctx.input.mosaic = "无码"
    data = await JavdbCrawler(client=None)._parse_detail_page(ctx, html, "https://javdb.com/v/example")

    assert data.actors == ["演员A"]
    assert data.all_actors == ["演员A"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "markup",
    [
        '<span><a class="actor-male" href="/actors/m">男演员</a></span>'
        '<span><a class="tag actor-female" href="/actors/f"> 女演员 </a></span>',
        '<span><a href="/actors/m">男演员</a><strong class="male">♂</strong>'
        '<a href="/actors/f"> 女演员 </a><strong class="female">♀</strong></span>',
        '<span><a href="/actors/m">男演员</a><strong class="male">♂</strong></span>'
        '<span><a href="/actors/f"> 女演员 </a><strong class="female">♀</strong></span>',
    ],
)
async def test_gender_selection_in_new_and_legacy_markup(markup):
    html = Selector('<a href="/actors">演员导航</a>' + markup)
    parser = Parser()
    ctx = Context(input=CrawlerInput.empty())

    assert await parser.actors(ctx, html) == ["女演员"]
    assert await parser.all_actors(ctx, html) == ["男演员", "女演员"]


@pytest.mark.asyncio
async def test_male_only_page_does_not_supply_female_actors():
    html = Selector('<a class="actor-male" href="/actors/m">男演员</a>')
    ctx = Context(input=CrawlerInput.empty())
    assert await Parser().actors(ctx, html) == []
    assert await Parser().all_actors(ctx, html) == ["男演员"]
