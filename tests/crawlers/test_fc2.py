import pytest
from lxml import etree

from mdcx.config.enums import Language
from mdcx.config.manager import manager
from mdcx.crawlers.fc2 import Fc2Crawler, getOutline
from mdcx.models.types import CrawlerInput


class FakeFc2Client:
    async def get_text(self, url, **kwargs):
        if url == "https://adult.contents.fc2.com/article/1723984/":
            return (
                """
                <html>
                  <head>
                    <title>FC2 sample</title>
                    <script type="application/ld+json">{"aggregateRating":{"ratingValue":"4.5"}}</script>
                  </head>
                  <body>
                    <section class="items_article_wrapper"></section>
                    <div data-section="userInfo"><h3><span></span> Sample Title</h3></div>
                    <ul class="items_article_SampleImagesArea">
                      <li><a href="//example.test/sample1.jpg"></a></li>
                    </ul>
                    <div class="items_article_MainitemThumb"><span><img src="//example.test/thumb.jpg" /></span></div>
                    <div class="items_article_Releasedate"><p>2026/04/03</p></div>
                    <div class="items_article_headerInfo"><ul><li><a>分类</a></li><li><a>卖家</a></li></ul></div>
                    <a class="tag tagTag">無修正</a><a class="tag tagTag">素人</a>
                    <section class="items_article_Contents">商品説明 紹介文</section>
                    <p class="items_article_info">01:02:03</p>
                  </body>
                </html>
                """,
                "",
            )
        if url == "https://adult.contents.fc2.com/api/v2/videos/1723984/sample":
            return '{"path":"https://example.test/sample.mp4?mid=token"}', ""
        return None, f"unexpected url: {url}"


@pytest.mark.parametrize("label", ["【看更多】", "查看更多", "もっと見る", "Read more"])
def test_fc2_outline_ignores_expand_ui_without_real_description(label):
    html = etree.fromstring(
        f'<html><section class="items_article_Contents"><button>{label}</button></section></html>',
        etree.HTMLParser(),
    )

    assert getOutline(html) == ""


def test_fc2_outline_keeps_real_description_while_ignoring_expand_ui():
    html = etree.fromstring(
        """
        <html><section class="items_article_Contents">
          <h3>商品説明</h3><p>真正的影片简介</p><button>【看更多】</button>
        </section></html>
        """,
        etree.HTMLParser(),
    )

    assert getOutline(html) == "真正的影片简介"


@pytest.mark.asyncio
async def test_fc2_crawler_maps_detail_and_sample_api(monkeypatch):
    monkeypatch.setattr(manager.config, "fields_rule", "")
    crawler = Fc2Crawler(client=FakeFc2Client())
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-1723984",
            short_number="FC2-1723984",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.debug_info.error is None
    assert res.data is not None
    assert res.data.number == "FC2-1723984"
    assert res.data.title == "Sample Title"
    assert res.data.tags == ["素人"]
    assert res.data.release == "2026-04-03"
    assert res.data.year == "2026"
    assert res.data.runtime == "62"
    assert res.data.score == "4.5"
    assert res.data.trailer == "https://example.test/sample.mp4?mid=token"
    assert res.data.source == "fc2"
