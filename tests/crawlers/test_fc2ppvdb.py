import html
import json

import pytest

from mdcx.config.enums import Language
from mdcx.config.manager import manager
from mdcx.crawlers.fc2ppvdb import (
    Fc2ppvdbCrawler,
    cookie_str_to_dict,
    has_fc2cmadb_session,
    parse_article_page,
)
from mdcx.models.types import CrawlerInput


class FakeFc2ppvdbClient:
    def __init__(self):
        self.requested_urls = []

    async def request(self, method, url, **kwargs):
        assert method == "GET"
        self.requested_urls.append(url)
        if url == "https://fc2cmadb.com/articles/3259498":

            class ArticleResponse:
                status_code = 200
                headers = {"content-type": "text/html; charset=utf-8"}
                text = make_article_page()

            return ArticleResponse(), ""

        raise AssertionError(f"unexpected request: {url}")


class FakeFc2ppvdbHtmlClient:
    async def request(self, method, url, **kwargs):
        assert method == "GET"

        class ArticleResponse:
            status_code = 200
            headers = {"content-type": "text/html; charset=UTF-8"}
            text = "<!DOCTYPE html><html><title>FC2PPVDB</title><body>ログイン</body></html>"

        return ArticleResponse(), ""


def make_article_page() -> str:
    page = {
        "component": "Articles/Show",
        "props": {
            "article": {
                "title": "FC2 Sample",
                "image_url": "https://example.test/cover.jpg",
                "release_date": "2026-04-02",
                "actresses": [{"name": "演员A"}],
                "tags": [{"name": "無修正"}, {"name": "素人"}],
                "writer": {"name": "卖家"},
                "censored": None,
                "duration": "01:05:30",
            }
        },
    }
    return f'<html><script type="application/json" data-page>{html.escape(json.dumps(page))}</script></html>'


@pytest.mark.asyncio
async def test_fc2ppvdb_crawler_reads_article_from_detail_page(monkeypatch):
    monkeypatch.setattr(manager.config, "fields_rule", "")
    client = FakeFc2ppvdbClient()
    crawler = Fc2ppvdbCrawler(client=client)
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-PPV-3259498",
            short_number="FC2-PPV-3259498",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.debug_info.error is None
    assert res.data is not None
    assert res.data.number == "FC2-3259498"
    assert res.data.title == "FC2 Sample"
    assert res.data.actors == ["演员A"]
    assert res.data.tags == ["素人"]
    assert res.data.runtime == "65"
    assert res.data.mosaic == "无码"
    assert res.data.external_id == "https://fc2cmadb.com/articles/3259498"
    assert client.requested_urls == ["https://fc2cmadb.com/articles/3259498"]


def test_fc2cmadb_cookie_parser_accepts_cookie_without_spaces():
    assert cookie_str_to_dict("foo=bar;fc2cmadb-session=abc; theme=dark") == {
        "foo": "bar",
        "fc2cmadb-session": "abc",
        "theme": "dark",
    }


def test_fc2cmadb_session_check_rejects_legacy_cookie_name():
    assert has_fc2cmadb_session("fc2cmadb-session=abc; ageVerified=true") is True
    assert has_fc2cmadb_session("fc2ppvdb_session=abc") is False


def test_parse_article_page_reads_inertia_page_data():
    data = parse_article_page(make_article_page())

    assert data["article"]["title"] == "FC2 Sample"


@pytest.mark.asyncio
async def test_fc2ppvdb_crawler_reports_login_page(monkeypatch):
    monkeypatch.setattr(manager.config, "fields_rule", "")
    crawler = Fc2ppvdbCrawler(client=FakeFc2ppvdbHtmlClient())
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-3259498",
            short_number="FC2-3259498",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.data is None
    assert res.debug_info.error is not None
    assert "fc2cmadb Cookie 可能无效或已过期" in str(res.debug_info.error)
