import sys
import threading
from types import SimpleNamespace

import pytest

from mdcx.config.enums import Website
from mdcx.core.network_check import (
    NetworkCheckSpec,
    NetworkCheckStatus,
    build_network_check_specs,
    format_result_line,
    run_network_check,
    run_network_check_item,
)


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "ok", url: str = "https://example.test"):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = {}
        self.encoding = "utf-8"


class FakeClient:
    def __init__(self, *, fail_url_part: str = ""):
        self.fail_url_part = fail_url_part
        self.calls: list[dict] = []

    async def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.fail_url_part and self.fail_url_part in url:
            raise RuntimeError("boom")
        return FakeResponse(url=url), ""


class FakeBypassClient:
    def __init__(self, *, bypass_ok: bool = True):
        self.bypass_ok = bypass_ok
        self.calls: list[dict] = []
        self.bypass_calls: list[dict] = []

    async def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse(
            text="<html><title>Just a moment...</title><script src='/cdn-cgi/challenge-platform/x'></script>Cloudflare</html>",
            url=url,
        ), ""

    async def _try_bypass_cloudflare(self, **kwargs):
        self.bypass_calls.append(kwargs)
        if not self.bypass_ok:
            return None, "bypass failed"
        response = FakeResponse(text="<html>ok</html>", url=kwargs["target_url"])
        response.headers["x-mdcx-bypass-mode"] = "mirror"
        return response, ""


class FakeConfig:
    use_proxy = False
    proxy = ""
    cf_bypass_url = ""
    cf_bypass_proxy = ""
    timeout = 5
    javdb = ""
    javbus = ""
    fc2ppvdb = ""
    theporndb_api_token = ""

    def get_site_url(self, site, default=""):
        return default


class FakeManager:
    config = FakeConfig()
    computed = None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fake_manager(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: FakeManager())


@pytest.mark.anyio
async def test_build_network_check_specs_uses_registered_sites_without_key_error(monkeypatch: pytest.MonkeyPatch):
    class DynamicCrawler:
        @classmethod
        def base_url_(cls):
            return ""

    class CustomConfig(FakeConfig):
        def get_site_url(self, site, default=""):
            return "https://custom.example"

    class CustomManager:
        config = CustomConfig()
        computed = None

    fake_crawlers = SimpleNamespace(
        get_registered_crawler_sites=lambda include_hidden=False: [Website.OFFICIAL],
        get_crawler=lambda site: DynamicCrawler,
    )
    monkeypatch.setitem(sys.modules, "mdcx.crawlers", fake_crawlers)
    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: CustomManager())

    specs = await build_network_check_specs()

    assert any(spec.site == Website.OFFICIAL and spec.url == "https://custom.example" for spec in specs)


@pytest.mark.anyio
async def test_run_network_check_item_catches_single_item_exception():
    spec = NetworkCheckSpec(name="bad", group="刮削站点", url="https://bad.example")

    result = await run_network_check_item(spec, client=FakeClient(fail_url_part="bad"))

    assert result.status == NetworkCheckStatus.FAILED
    assert result.message == "检测异常"
    assert result.error == "boom"


@pytest.mark.anyio
async def test_run_network_check_does_not_stop_on_single_item_exception(monkeypatch: pytest.MonkeyPatch):
    async def fake_specs():
        return [
            NetworkCheckSpec(name="good", group="基础连通性", url="https://good.example"),
            NetworkCheckSpec(name="bad", group="基础连通性", url="https://bad.example"),
        ]

    monkeypatch.setattr("mdcx.core.network_check.build_network_check_specs", fake_specs)
    lines: list[str] = []

    results = await run_network_check(
        progress=lines.append, client=FakeClient(fail_url_part="bad"), concurrency=2, emit_header=False
    )

    assert len(results) == 2
    assert {result.spec.name: result.status for result in results} == {
        "good": NetworkCheckStatus.OK,
        "bad": NetworkCheckStatus.FAILED,
    }
    assert any("网络检测已完成" in line for line in lines)


@pytest.mark.anyio
async def test_run_network_check_can_cancel_between_groups(monkeypatch: pytest.MonkeyPatch):
    async def fake_specs():
        return [
            NetworkCheckSpec(name="first", group="基础连通性", url="https://first.example"),
            NetworkCheckSpec(name="second", group="刮削站点", url="https://second.example"),
        ]

    monkeypatch.setattr("mdcx.core.network_check.build_network_check_specs", fake_specs)
    cancel_event = threading.Event()
    lines: list[str] = []

    def progress(line: str):
        lines.append(line)
        if "first" in line:
            cancel_event.set()

    results = await run_network_check(
        progress=progress, cancel_event=cancel_event, client=FakeClient(), concurrency=1, emit_header=False
    )

    assert [result.spec.name for result in results] == ["first"]
    assert any("网络检测已取消" in line for line in lines)


@pytest.mark.anyio
async def test_javdbapi_spec_uses_real_query_url(monkeypatch: pytest.MonkeyPatch):
    class ApiCrawler:
        @classmethod
        def base_url_(cls):
            return "https://api.thejavdb.net/v1"

    fake_crawlers = SimpleNamespace(
        get_registered_crawler_sites=lambda include_hidden=False: [Website.JAVDBAPI],
        get_crawler=lambda site: ApiCrawler,
    )
    monkeypatch.setitem(sys.modules, "mdcx.crawlers", fake_crawlers)

    specs = await build_network_check_specs()

    javdbapi = next(spec for spec in specs if spec.site == Website.JAVDBAPI)
    assert javdbapi.url == "https://api.thejavdb.net/v1/movies?q=ssni-200"
    assert javdbapi.validator == "javdbapi"


@pytest.mark.anyio
async def test_network_specs_always_list_fc2cmadb_even_though_it_is_hidden_from_generic_ui(
    monkeypatch: pytest.MonkeyPatch,
):
    class Fc2Crawler:
        @classmethod
        def base_url_(cls):
            return "https://fc2cmadb.com"

    fake_crawlers = SimpleNamespace(
        get_registered_crawler_sites=lambda include_hidden=False: [],
        get_crawler=lambda site: Fc2Crawler if site == Website.FC2PPVDB else None,
    )
    monkeypatch.setitem(sys.modules, "mdcx.crawlers", fake_crawlers)

    specs = await build_network_check_specs()

    fc2cmadb = next(spec for spec in specs if spec.site == Website.FC2PPVDB)
    assert fc2cmadb.name == "fc2cmadb"
    assert fc2cmadb.url.startswith("https://fc2cmadb.com/articles/")
    assert "Cookie" in fc2cmadb.warning_if_missing


@pytest.mark.anyio
async def test_fc2cmadb_network_check_validates_configured_cookie(monkeypatch: pytest.MonkeyPatch):
    class CookieConfig(FakeConfig):
        fc2ppvdb = "fc2cmadb-session=session-token; ageVerified=true"

    class CookieManager:
        config = CookieConfig()
        computed = None

    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: CookieManager())
    spec = NetworkCheckSpec(
        name="fc2cmadb",
        group="刮削站点",
        url="https://fc2cmadb.com/articles/1817847",
        site=Website.FC2PPVDB,
        cookies={"fc2cmadb-session": "session-token"},
        validator="fc2cmadb",
    )
    client = FakeClient()
    page = '<script type="application/json" data-page>{"component": "Articles/Show", "props": {"article": {"id": 1817847}}}</script><a href="/login">Login</a>'

    async def request(method, url, **kwargs):
        client.calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse(text=page, url=url), ""

    client.request = request
    result = await run_network_check_item(spec, client=client)

    assert result.status == NetworkCheckStatus.OK
    assert result.message == "连接正常，Cookie 有效"
    assert client.calls[0]["cookies"]["fc2cmadb-session"] == "session-token"
    assert client.calls[0]["fingerprint_id"] == "chrome136_win"


@pytest.mark.anyio
async def test_fc2cmadb_http_404_is_reported_as_cookie_failure_not_network_outage():
    class HttpErrorClient:
        async def request(self, method, url, **kwargs):
            return None, f"GET {url} 失败: HTTP 404"

    spec = NetworkCheckSpec(
        name="fc2cmadb",
        group="刮削站点",
        url="https://fc2cmadb.com/articles/1817847",
        site=Website.FC2PPVDB,
        validator="fc2cmadb",
    )
    result = await run_network_check_item(spec, client=HttpErrorClient())
    assert result.status == NetworkCheckStatus.WARNING
    assert result.status_code == 404
    assert result.message == "站点可访问，但 FC2CMADB Cookie 无效或已过期"
    assert result.error == ""


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("site", "name", "status_code"),
    [(Website.JAVDB, "javdb", 403), (Website.JAVBUS, "javbus", 404)],
)
async def test_cookie_site_http_errors_are_not_reported_as_network_outage(site, name, status_code):
    class HttpErrorClient:
        async def request(self, method, url, **kwargs):
            return None, f"GET {url} 失败: HTTP {status_code}"

    spec = NetworkCheckSpec(
        name=name,
        group="刮削站点",
        url=f"https://{name}.example/detail",
        site=site,
        headers={"cookie": "configured"},
    )
    result = await run_network_check_item(spec, client=HttpErrorClient())
    assert result.status == NetworkCheckStatus.WARNING
    assert result.status_code == status_code
    assert "站点可访问" in result.message
    assert "Cookie" in result.message
    assert result.error == ""


@pytest.mark.anyio
async def test_fc2cmadb_network_check_validates_page_after_cf_bypass(monkeypatch: pytest.MonkeyPatch):
    class BypassConfig(FakeConfig):
        fc2ppvdb = "fc2cmadb-session=session-token"
        cf_bypass_url = "http://127.0.0.1:8000"

    class BypassManager:
        config = BypassConfig()
        computed = None

    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: BypassManager())
    client = FakeBypassClient()

    async def bypass_login_page(**kwargs):
        client.bypass_calls.append(kwargs)
        return FakeResponse(text="<html>Login</html>", url=kwargs["target_url"]), ""

    client._try_bypass_cloudflare = bypass_login_page
    spec = NetworkCheckSpec(
        name="fc2cmadb",
        group="刮削站点",
        url="https://fc2cmadb.com/articles/1817847",
        site=Website.FC2PPVDB,
        validator="fc2cmadb",
        enable_cf_bypass=True,
    )

    result = await run_network_check_item(spec, client=client)

    assert result.status == NetworkCheckStatus.FAILED
    assert result.message == "站点可访问，但 FC2CMADB Cookie 未生效"


def test_format_result_line_does_not_duplicate_error():
    spec = NetworkCheckSpec(name="site", group="刮削站点", url="https://example.test")
    from mdcx.core.network_check import NetworkCheckResult

    result = NetworkCheckResult(
        spec=spec,
        status=NetworkCheckStatus.FAILED,
        message="GET https://example.test 失败: HTTP 403",
        error="GET https://example.test 失败: HTTP 403",
    )

    line = format_result_line(result)

    assert line.count("GET https://example.test 失败: HTTP 403") == 1


def test_format_result_line_shows_url_for_scraper_sites():
    from mdcx.core.network_check import NetworkCheckResult

    spec = NetworkCheckSpec(name="javdb", group="刮削站点", url="https://javdb.example/v/ABC")
    result = NetworkCheckResult(spec=spec, status=NetworkCheckStatus.OK, message="连接正常")
    line = format_result_line(result)
    assert "URL: https://javdb.example/v/ABC" in line


@pytest.mark.anyio
async def test_run_network_check_item_actively_uses_cf_bypass_on_challenge(monkeypatch: pytest.MonkeyPatch):
    class BypassConfig(FakeConfig):
        cf_bypass_url = "http://0.0.0.0:8000"

    class BypassManager:
        config = BypassConfig()
        computed = None

    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: BypassManager())
    client = FakeBypassClient()
    spec = NetworkCheckSpec(
        name="cf-site",
        group="刮削站点",
        url="https://cf.example",
        enable_cf_bypass=True,
        headers={"cookie": "a=b"},
    )

    result = await run_network_check_item(spec, client=client)

    assert result.status == NetworkCheckStatus.OK
    assert result.message == "连接正常，已通过 CF Bypass（mirror）"
    assert client.bypass_calls[0]["target_url"] == "https://cf.example"
    assert client.bypass_calls[0]["headers"] == {"cookie": "a=b"}
    assert client.bypass_calls[0]["timeout"] is None


@pytest.mark.anyio
async def test_run_network_check_item_reports_cf_bypass_failure(monkeypatch: pytest.MonkeyPatch):
    class BypassConfig(FakeConfig):
        cf_bypass_url = "http://0.0.0.0:8000"

    class BypassManager:
        config = BypassConfig()
        computed = None

    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: BypassManager())
    spec = NetworkCheckSpec(
        name="cf-site",
        group="刮削站点",
        url="https://cf.example",
        enable_cf_bypass=True,
    )

    result = await run_network_check_item(spec, client=FakeBypassClient(bypass_ok=False))

    assert result.status == NetworkCheckStatus.FAILED
    assert result.message == "Cloudflare Bypass 失败"
    assert result.error == "bypass failed"


def test_bypass_http_error_with_proxy_query_is_not_proxy_failure():
    from mdcx.core.network_check import _message_for_error

    error = "GET http://service.test/cookies?proxy=http%3A%2F%2Fproxy.test 失败: HTTP 404"
    assert _message_for_error(error) == error


@pytest.mark.anyio
async def test_flaresolverr_health_uses_service_detection():
    class Client:
        async def _detect_cf_bypass_service(self):
            return "flaresolverr"

        async def request(self, method, url, **kwargs):
            assert url == "http://service.test"
            assert kwargs["use_proxy"] is False
            return FakeResponse(text='{"msg":"FlareSolverr is ready!"}'), ""

    spec = NetworkCheckSpec(
        name="CF Bypass", group="辅助服务", url="http://service.test/cookies?url=http://example.com", use_proxy=False
    )
    result = await run_network_check_item(spec, client=Client())
    assert result.status == NetworkCheckStatus.OK
    assert "FlareSolverr" in result.message


@pytest.mark.anyio
@pytest.mark.parametrize("script", ["jsd", "precursor"])
async def test_normal_cloudflare_page_does_not_trigger_bypass(monkeypatch, script):
    class Config(FakeConfig):
        cf_bypass_url = "http://service.test"

    monkeypatch.setattr("mdcx.core.network_check._manager", lambda: SimpleNamespace(config=Config()))

    class Client:
        async def request(self, *args, **kwargs):
            return FakeResponse(
                text=(
                    "<html><title>Site catalogue</title><main>Movie list</main>"
                    f'<script src="/cdn-cgi/challenge-platform/scripts/{script}/main.js"></script>'
                    '<script src="https://static.cloudflareinsights.com/beacon.min.js"></script></html>'
                )
            ), ""

        async def _try_bypass_cloudflare(self, **kwargs):
            raise AssertionError("Normal HTML must not trigger bypass")

    spec = NetworkCheckSpec(name="site", group="刮削站点", url="https://site.test", enable_cf_bypass=True)
    result = await run_network_check_item(spec, client=Client())
    assert result.status == NetworkCheckStatus.OK
    assert result.message == "连接正常"
