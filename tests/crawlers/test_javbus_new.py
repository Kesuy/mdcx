import pytest

from mdcx.config.enums import Language
from mdcx.crawlers.javbus import JavbusCrawler
from mdcx.models.types import CrawlerInput


class FakeJavbusClient:
    async def get_text(self, url, **kwargs):
        assert url == "https://www.javbus.com/SSIS-243"
        assert "headers" in kwargs
        return (
            """
            <html>
              <body>
                <li class="active"><a>有碼</a></li>
                <h3>SSIS-243 Sample Title</h3>
                <p><span class="header">識別碼:</span><span>SSIS-243</span></p>
                <p><span class="header">發行日期:</span>2026/04/03</p>
                <p><span class="header">長度:</span>120分鐘</p>
                <a class="bigImage" href="/pics/cover/ssis243_b.jpg"></a>
                <div class="star-name"><a>演员A</a></div>
                <span class="genre"><label><a href="/genre/a">剧情</a></label></span>
                <a href="/studio/abc">制作商</a>
                <a href="/label/abc">发行商</a>
                <a href="/director/abc">导演</a>
                <a href="/series/abc">系列</a>
                <div id="sample-waterfall"><a href="/sample1.jpg"></a></div>
              </body>
            </html>
            """,
            "",
        )


class FakeUncensoredJavbusClient:
    def __init__(self, detail_number: str = "FDD-2007"):
        self.calls: list[str] = []
        self.detail_number = detail_number

    async def get_text(self, url, **kwargs):
        self.calls.append(url)
        assert "headers" in kwargs
        if "/uncensored/search/" in url:
            return f'<a class="movie-box" href="https://www.javbus.com/{self.detail_number}"></a>', ""
        assert url == f"https://www.javbus.com/{self.detail_number}"
        return (
            f"""
            <html>
              <body>
                <li class="active"><a>無碼</a></li>
                <h3>{self.detail_number} Uncensored Sample</h3>
                <p><span class="header">識別碼:</span><span>{self.detail_number}</span></p>
                <p><span class="header">發行日期:</span>2007-01-01</p>
                <a class="bigImage" href="/imgs/cover/fdd2007_b.jpg"></a>
              </body>
            </html>
            """,
            "",
        )


@pytest.mark.asyncio
async def test_javbus_crawler_maps_detail_page():
    crawler = JavbusCrawler(client=FakeJavbusClient(), base_url="https://www.javbus.com")
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="SSIS-243",
            short_number="SSIS-243",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.debug_info.error is None
    assert res.data is not None
    assert res.data.number == "SSIS-243"
    assert res.data.title == "Sample Title"
    assert res.data.actors == ["演员A"]
    assert res.data.tags == ["剧情"]
    assert res.data.release == "2026-04-03"
    assert res.data.runtime == "120"
    assert res.data.studio == "制作商"
    assert res.data.publisher == "发行商"
    assert res.data.directors == ["导演"]
    assert res.data.series == "系列"
    assert res.data.source == "javbus"


@pytest.mark.asyncio
async def test_javbus_uncensored_uses_search_namespace_before_detail():
    client = FakeUncensoredJavbusClient()
    crawler = JavbusCrawler(client=client, base_url="https://www.javbus.com")
    crawler_input = CrawlerInput.empty()
    crawler_input.number = "FDD-2007"
    crawler_input.short_number = crawler_input.number
    crawler_input.mosaic = "无码"

    res = await crawler.run(crawler_input)

    assert res.debug_info.error is None
    assert res.debug_info.search_urls == ["https://www.javbus.com/uncensored/search/FDD-2007&type=0&parent=uc"]
    assert res.data is not None
    assert res.data.number == "FDD-2007"
    assert res.data.title == "Uncensored Sample"
    assert client.calls == [
        "https://www.javbus.com/uncensored/search/FDD-2007&type=0&parent=uc",
        "https://www.javbus.com/FDD-2007",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested_number", "site_number"),
    [
        ("FZ65", "FZ-65"),
        ("FZ-65", "FZ65"),
        ("FDD2007", "FDD-2007"),
        ("FDD-2007", "FDD2007"),
    ],
)
async def test_javbus_uncensored_matches_separator_variants(requested_number: str, site_number: str):
    client = FakeUncensoredJavbusClient(site_number)
    crawler = JavbusCrawler(client=client, base_url="https://www.javbus.com")
    crawler_input = CrawlerInput.empty()
    crawler_input.number = requested_number
    crawler_input.short_number = requested_number
    crawler_input.mosaic = "无码"

    response = await crawler.run(crawler_input)

    assert response.debug_info.error is None
    assert response.data is not None
    assert response.data.number == site_number
    assert client.calls == [
        f"https://www.javbus.com/uncensored/search/{requested_number}&type=0&parent=uc",
        f"https://www.javbus.com/{site_number}",
    ]
