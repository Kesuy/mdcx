import html
import json

import pytest

from mdcx.config.enums import Language
from mdcx.config.manager import manager
from mdcx.crawlers.fc2ppvdb import (
    FC2CMADB_AUTH_PROBE_NUMBER,
    Fc2ppvdbCrawler,
    cookie_str_to_dict,
    fetch_article_info,
    has_fc2cmadb_session,
    parse_article_page,
    validate_fc2cmadb_cookie,
)
from mdcx.models.types import CrawlerInput


class FakeFc2ppvdbClient:
    def __init__(self):
        self.requests = []

    async def request(self, method, url, **kwargs):
        assert method == "GET"
        self.requests.append((url, kwargs))
        if url == "https://fc2cmadb.com/articles/2701833":
            headers = kwargs.get("headers") or {}
            if headers.get("X-Inertia-Partial-Data") == "actresses":

                class DeferredResponse:
                    status_code = 200
                    headers = {"content-type": "application/json"}
                    text = json.dumps(
                        {
                            "component": "Articles/Show",
                            "props": {"actresses": [{"id": 3908, "name": "九野ひなの"}]},
                            "url": "/articles/2701833",
                        },
                        ensure_ascii=False,
                    )

                return DeferredResponse(), ""

            class ArticleResponse:
                status_code = 200
                headers = {"content-type": "text/html; charset=utf-8"}
                text = make_article_page()

            return ArticleResponse(), ""

        raise AssertionError(f"unexpected request: {url}")


class FakeFc2ppvdbHtmlClient:
    def __init__(self):
        self.requests = 0

    async def request(self, method, url, **kwargs):
        assert method == "GET"
        self.requests += 1

        class ArticleResponse:
            status_code = 200
            headers = {"content-type": "text/html; charset=UTF-8"}
            text = "<!DOCTYPE html><html><title>FC2PPVDB</title><body>ログイン</body></html>"

        return ArticleResponse(), ""


def make_article_page(*, deferred: bool = True) -> str:
    article = {
        "title": "FC2 Sample",
        "image_url": "https://example.test/cover.jpg",
        "release_date": "2026-04-02",
        "tags": [{"name": "無修正"}, {"name": "素人"}],
        "writer": {"name": "卖家"},
        "censored": None,
        "duration": "01:05:30",
    }
    if not deferred:
        article["actresses"] = [{"name": "内联演员"}]

    page = {
        "component": "Articles/Show",
        "version": "asset-version-20260726",
        "props": {"article": article},
    }
    if deferred:
        page["deferredProps"] = {"default": ["actresses"]}
    return f'<html><script type="application/json" data-page>{html.escape(json.dumps(page))}</script></html>'


@pytest.mark.asyncio
async def test_fc2ppvdb_crawler_reads_article_from_detail_page(monkeypatch):
    monkeypatch.setattr(manager.config, "fields_rule", "fc2_seller")
    client = FakeFc2ppvdbClient()
    crawler = Fc2ppvdbCrawler(client=client)
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-PPV-2701833",
            short_number="FC2-PPV-2701833",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.debug_info.error is None
    assert res.data is not None
    assert res.data.number == "FC2-2701833"
    assert res.data.title == "FC2 Sample"
    assert res.data.outline == ""
    assert res.data.originalplot == ""
    assert res.data.actors == ["九野ひなの"]
    assert res.data.tags == ["素人"]
    assert res.data.runtime == "65"
    assert res.data.mosaic == "无码"
    assert res.data.image_download is True
    assert res.data.external_id == "https://fc2cmadb.com/articles/2701833"
    assert [url for url, _kwargs in client.requests] == [
        "https://fc2cmadb.com/articles/2701833",
        "https://fc2cmadb.com/articles/2701833",
    ]
    assert client.requests[1][1]["headers"] == {
        "Accept": "text/html, application/xhtml+xml",
        "X-Inertia": "true",
        "X-Inertia-Partial-Component": "Articles/Show",
        "X-Inertia-Partial-Data": "actresses",
        "X-Inertia-Version": "asset-version-20260726",
        "X-Requested-With": "XMLHttpRequest",
    }


@pytest.mark.asyncio
async def test_fetch_article_info_uses_rotated_cookie_for_deferred_request():
    cookies = {
        "ageVerified": "true",
        "XSRF-TOKEN": "old-xsrf",
        "fc2cmadb-session": "old-session",
    }

    class RotatingClient:
        async def request(self, method, url, **kwargs):
            headers = kwargs.get("headers") or {}
            if headers.get("X-Inertia-Partial-Data") == "actresses":
                assert kwargs["cookies"]["XSRF-TOKEN"] == "new-xsrf"
                assert kwargs["cookies"]["fc2cmadb-session"] == "new-session"

                class DeferredResponse:
                    status_code = 200
                    headers = {"content-type": "application/json"}
                    text = json.dumps(
                        {
                            "component": "Articles/Show",
                            "props": {"actresses": [{"name": "小山紗智子"}]},
                        },
                        ensure_ascii=False,
                    )

                return DeferredResponse(), ""

            class ArticleResponse:
                status_code = 200
                headers = {
                    "content-type": "text/html; charset=utf-8",
                    "set-cookie": "XSRF-TOKEN=new-xsrf; Path=/, fc2cmadb-session=new-session; Path=/; HttpOnly",
                }
                text = make_article_page()

            return ArticleResponse(), ""

    data, error = await fetch_article_info(
        RotatingClient(),
        base_url="https://fc2cmadb.com",
        number="1887986",
        cookies=cookies,
        use_proxy=False,
    )

    assert error == ""
    assert data is not None
    assert cookies["XSRF-TOKEN"] == "new-xsrf"
    assert cookies["fc2cmadb-session"] == "new-session"


@pytest.mark.asyncio
async def test_fc2ppvdb_crawler_persists_rotated_cookie(monkeypatch):
    class RotatingInlineClient:
        async def request(self, method, url, **kwargs):
            class Response:
                status_code = 200
                headers = {
                    "content-type": "text/html; charset=utf-8",
                    "set-cookie": "XSRF-TOKEN=new-xsrf; Path=/, fc2cmadb-session=new-session; Path=/; HttpOnly",
                }
                text = make_article_page(deferred=False)

            return Response(), ""

    save_calls = []
    monkeypatch.setattr(manager.config, "fields_rule", "")
    monkeypatch.setattr(
        manager.config,
        "fc2ppvdb",
        "ageVerified=true; XSRF-TOKEN=old-xsrf; fc2cmadb-session=old-session",
    )
    monkeypatch.setattr(manager, "save", lambda: save_calls.append(True))

    crawler = Fc2ppvdbCrawler(client=RotatingInlineClient())
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-1887986",
            short_number="FC2-1887986",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.debug_info.error is None
    saved_cookies = cookie_str_to_dict(manager.config.fc2ppvdb)
    assert saved_cookies["XSRF-TOKEN"] == "new-xsrf"
    assert saved_cookies["fc2cmadb-session"] == "new-session"
    assert save_calls == [True]


def test_fc2cmadb_cookie_parser_accepts_cookie_without_spaces():
    assert cookie_str_to_dict("foo=bar;fc2cmadb-session=abc; theme=dark") == {
        "foo": "bar",
        "fc2cmadb-session": "abc",
        "theme": "dark",
    }


def test_fc2cmadb_session_check_rejects_legacy_cookie_name():
    assert has_fc2cmadb_session("fc2cmadb-session=abc; ageVerified=true") is True
    assert has_fc2cmadb_session("fc2ppvdb_session=abc") is False


@pytest.mark.asyncio
async def test_fc2cmadb_cookie_validation_uses_login_only_article():
    class AuthenticatedClient:
        def __init__(self):
            self.urls = []

        async def request(self, method, url, **kwargs):
            self.urls.append(url)
            assert kwargs["fingerprint_id"] == "chrome136_win"

            class Response:
                status_code = 200
                headers = {"content-type": "text/html; charset=utf-8"}
                text = make_article_page(deferred=False)

            return Response(), ""

    client = AuthenticatedClient()

    valid, error = await validate_fc2cmadb_cookie(
        client,
        "fc2cmadb-session=session-token; ageVerified=true",
        use_proxy=False,
    )

    assert valid is True
    assert error == ""
    assert client.urls == [f"https://fc2cmadb.com/articles/{FC2CMADB_AUTH_PROBE_NUMBER}"]


@pytest.mark.asyncio
async def test_fc2cmadb_cookie_validation_rejects_expired_session_returning_404():
    class ExpiredClient:
        async def request(self, method, url, **kwargs):
            return None, f"GET {url} 失败: HTTP 404"

    valid, error = await validate_fc2cmadb_cookie(
        ExpiredClient(),
        "fc2cmadb-session=expired-token",
        use_proxy=False,
    )

    assert valid is False
    assert "Cookie 无效或已过期" in error


@pytest.mark.asyncio
async def test_fc2cmadb_cookie_validation_does_not_report_cloudflare_failure_as_expired():
    class CloudflareBlockedClient:
        async def request(self, method, url, **kwargs):
            return None, f"GET {url} 失败: HTTP 403"

    valid, error = await validate_fc2cmadb_cookie(
        CloudflareBlockedClient(),
        "fc2cmadb-session=session-token",
        use_proxy=False,
    )

    assert valid is False
    assert error.startswith("暂时无法验证登录状态")
    assert "无效或已过期" not in error


def test_parse_article_page_reads_inertia_page_data():
    data = parse_article_page(make_article_page())

    assert data["article"]["title"] == "FC2 Sample"


@pytest.mark.asyncio
async def test_fetch_article_info_keeps_inline_actresses_without_partial_request():
    class InlineClient:
        def __init__(self):
            self.requests = []

        async def request(self, method, url, **kwargs):
            self.requests.append((method, url, kwargs))

            class Response:
                status_code = 200
                headers = {"content-type": "text/html; charset=utf-8"}
                text = make_article_page(deferred=False)

            return Response(), ""

    client = InlineClient()
    data, error = await fetch_article_info(
        client,
        base_url="https://fc2cmadb.com",
        number="2701833",
        cookies={"fc2cmadb-session": "session-token"},
        use_proxy=False,
    )

    assert error == ""
    assert data is not None
    assert data["article"]["actresses"] == [{"name": "内联演员"}]
    assert len(client.requests) == 1


@pytest.mark.asyncio
async def test_fc2ppvdb_crawler_reports_login_page(monkeypatch):
    monkeypatch.setattr(manager.config, "fields_rule", "")
    client = FakeFc2ppvdbHtmlClient()
    crawler = Fc2ppvdbCrawler(client=client)
    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-2701833",
            short_number="FC2-2701833",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.data is None
    assert res.debug_info.error is not None
    assert "登录" in str(res.debug_info.error)
    assert client.requests == 1


@pytest.mark.asyncio
async def test_fc2ppvdb_crawler_does_not_run_auth_recovery_on_cloudflare_403(monkeypatch):
    class CloudflareClient:
        def __init__(self):
            self.requests = 0

        async def request(self, method, url, **kwargs):
            self.requests += 1

            class Response:
                status_code = 403
                headers = {"cf-mitigated": "challenge"}
                text = "Just a moment..."

            return Response(), ""

    monkeypatch.setattr(manager.config, "fc2ppvdb", "fc2cmadb-session=current-session")
    client = CloudflareClient()
    crawler = Fc2ppvdbCrawler(client=client)

    res = await crawler.run(
        CrawlerInput(
            appoint_number="",
            appoint_url="",
            file_path=None,
            mosaic="",
            number="FC2-1887986",
            short_number="FC2-1887986",
            language=Language.UNDEFINED,
            org_language=Language.UNDEFINED,
        )
    )

    assert res.data is None
    assert "HTTP 403" in str(res.debug_info.error)
    assert client.requests == 1
