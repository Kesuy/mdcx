from pathlib import Path

import pytest
from parsel import Selector

from mdcx.crawlers.base import Context
from mdcx.crawlers.javdb_new import JavdbCrawler
from mdcx.models.types import CrawlerInput


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("number", "tag_count", "release", "runtime", "score", "actor_count", "mosaic"),
    [
        ("010625-001", 15, "2025-01-10", "61", "4.46", 1, "无码"),
        ("JURA-211", 6, "2026-09-03", "115", "3.67", 3, "有码"),
    ],
)
async def test_saved_page_metadata(number, tag_count, release, runtime, score, actor_count, mosaic):
    html = Selector((Path(__file__).parents[1] / "fixtures/javdb" / f"{number}.html").read_text(encoding="utf-8"))
    ctx = Context(input=CrawlerInput.empty())
    crawler = JavdbCrawler(client=None)
    data = await crawler._parse_detail_page(ctx, html, "https://javdb.com/v/example")
    result = await crawler.post_process(ctx, data.to_result())

    assert result.number == number
    assert result.title == "Sample"
    assert result.actors == ["Actor 1"]
    assert result.all_actors == [f"Actor {i}" for i in range(1, actor_count + 1)]
    assert result.tags == html.xpath('//strong[normalize-space(.)="類別:"]/../span/a/text()').getall()
    assert len(result.tags) == tag_count
    assert result.release == release
    assert result.year == release[:4]
    assert result.runtime == runtime
    assert result.score == score
    assert result.mosaic == mosaic
    assert result.publisher == ""
    if number == "JURA-211":
        assert result.studio == "センタービレッジ"
        assert result.directors == ["湊谷"]
        assert result.series == "初撮り人妻、ふたたび。"
    else:
        assert result.studio == result.series == ""
        assert result.directors == []
