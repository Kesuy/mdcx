import asyncio
import json
import random
from types import SimpleNamespace

import pytest
from curl_cffi.requests.exceptions import Timeout

from mdcx.web_async import AsyncWebClient, _ScopedCookie


def _fake_response(
    *,
    status_code: int,
    headers: dict[str, str] | None = None,
    content: bytes = b"ok",
    url: str = "",
):
    return SimpleNamespace(status_code=status_code, headers=headers or {}, content=content, url=url)


def _default_try_kwargs():
    return {
        "method": "GET",
        "headers": {},
        "cookies": None,
        "data": None,
        "json_data": None,
        "timeout": None,
        "allow_redirects": True,
        "use_proxy": False,
    }


def _patch_session_request(client: AsyncWebClient, request):
    class FakeSession:
        closed = False

        def __init__(self, _fingerprint=None):
            pass

        async def close(self):
            self.closed = True

        async def request(self, **kwargs):
            result = request(**kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result

    client._pool_manager._session_factory = FakeSession  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_detect_cf_bypass_service_recognizes_and_caches_flaresolverr():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8191")
    calls = 0

    async def fake_request(method, url, **kwargs):
        nonlocal calls
        calls += 1
        assert method == "GET"
        assert url == "http://127.0.0.1:8191"
        assert kwargs["enable_cf_bypass"] is False
        return (
            _fake_response(
                status_code=200,
                content=json.dumps({"msg": "FlareSolverr is ready!", "version": "3.5.0"}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            "",
        )

    client.request = fake_request  # type: ignore[method-assign]

    assert await client._detect_cf_bypass_service() == "flaresolverr"
    assert await client._detect_cf_bypass_service() == "flaresolverr"
    assert calls == 1


@pytest.mark.asyncio
async def test_call_flaresolverr_converts_solution_to_standard_response():
    client = AsyncWebClient(
        timeout=5,
        cf_bypass_url="http://127.0.0.1:8191",
        cf_bypass_proxy="http://127.0.0.1:7890",
    )
    captured: dict[str, object] = {}

    async def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        solution = {
            "status": "ok",
            "message": "Challenge solved!",
            "solution": {
                "url": "https://example.com/final",
                "status": 200,
                "headers": {"content-type": "text/html; charset=utf-8"},
                "response": "<html>solved</html>",
                "cookies": [{"name": "cf_clearance", "value": "token", "domain": ".example.com"}],
                "userAgent": "Mozilla/5.0 test",
            },
        }
        return _fake_response(status_code=200, content=json.dumps(solution).encode()), ""

    client.request = fake_request  # type: ignore[method-assign]

    response, error = await client._call_flaresolverr(
        "https://example.com/challenge",
        cookies={"session": "abc"},
        use_proxy=True,
    )

    assert error == ""
    assert response is not None
    assert response.status_code == 200
    assert response.content == b"<html>solved</html>"
    assert str(response.url) == "https://example.com/final"
    assert response.headers.get("x-mdcx-bypass-mode") == "flaresolverr"
    assert response.headers.get("x-mdcx-flaresolverr-user-agent") == "Mozilla/5.0 test"
    assert captured["method"] == "POST"
    assert captured["url"] == "http://127.0.0.1:8191/v1"
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["enable_cf_bypass"] is False
    payload = kwargs["json_data"]
    assert payload["cmd"] == "request.get"
    assert payload["url"] == "https://example.com/challenge"
    assert payload["maxTimeout"] == 45000
    assert payload["proxy"] == {"url": "http://127.0.0.1:7890"}
    assert payload["cookies"] == [
        {"name": "session", "value": "abc", "domain": "example.com"},
    ]
    assert client._flaresolverr_cookies_for_url("https://example.com/next") == {"cf_clearance": "token"}
    assert client._cf_flaresolverr_user_agent_by_host["example.com"] == "Mozilla/5.0 test"


@pytest.mark.asyncio
async def test_request_reuses_flaresolverr_cookies_and_user_agent():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8191")
    scoped = _ScopedCookie("cf_clearance", "solved", "example.com", "/", True, None, True)
    client._cf_flaresolverr_cookies[("example.com", "/", "cf_clearance", True)] = scoped
    client._cf_flaresolverr_user_agent_by_host["example.com"] = "FlareSolverr UA"
    captured: dict[str, object] = {}

    async def fake_curl_request(**kwargs):
        captured.update(kwargs)
        return _fake_response(status_code=200, content=b"ok")

    client._curl_request = fake_curl_request  # type: ignore[method-assign]
    response, error = await client.request(
        "GET",
        "https://example.com/article",
        headers={"User-Agent": "old ua"},
        cookies={"session": "original"},
        retry_count=1,
    )

    assert response is not None and error == ""
    assert captured["cookies"] == {"session": "original", "cf_clearance": "solved"}
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["User-Agent"] == "FlareSolverr UA"


def test_flaresolverr_cookies_respect_domain_path_secure_and_expiry():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8191")
    future = 4102444800.0
    cookies = [
        _ScopedCookie("parent", "yes", "example.com", "/", True, future, False),
        _ScopedCookie("host", "yes", "sub.example.com", "/private", True, future, True),
        _ScopedCookie("expired", "no", "sub.example.com", "/", False, 1.0, True),
    ]
    for cookie in cookies:
        client._cf_flaresolverr_cookies[(cookie.domain, cookie.path, cookie.name, cookie.host_only)] = cookie

    assert client._flaresolverr_cookies_for_url("https://sub.example.com/private/page") == {
        "parent": "yes",
        "host": "yes",
    }
    assert client._flaresolverr_cookies_for_url("http://sub.example.com/private/page") == {}
    assert client._flaresolverr_cookies_for_url("https://other.example.com/private/page") == {"parent": "yes"}
    assert client._flaresolverr_cookies_for_url("https://example.net/private/page") == {}


@pytest.mark.asyncio
async def test_flaresolverr_cross_domain_redirect_keeps_cookie_domains_isolated():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8191")

    async def fake_request(*args, **kwargs):
        solution = {
            "status": "ok",
            "solution": {
                "status": 200,
                "url": "https://final.example.net/page",
                "response": "<html>ok</html>",
                "cookies": [
                    {"name": "origin", "value": "o", "domain": ".origin.example.com", "path": "/"},
                    {"name": "final", "value": "f", "domain": ".final.example.net", "path": "/"},
                    {"name": "evil", "value": "x", "domain": ".evil.example.org", "path": "/"},
                ],
            },
        }
        return _fake_response(status_code=200, content=json.dumps(solution).encode()), ""

    client.request = fake_request  # type: ignore[method-assign]
    response, error = await client._call_flaresolverr(
        "https://origin.example.com/start",
        cookies=None,
        use_proxy=False,
    )

    assert response is not None and error == ""
    assert client._flaresolverr_cookies_for_url("https://origin.example.com/next") == {"origin": "o"}
    assert client._flaresolverr_cookies_for_url("https://final.example.net/next") == {"final": "f"}
    assert client._flaresolverr_cookies_for_url("https://evil.example.org/next") == {}


def test_flaresolverr_proxy_falls_back_to_enabled_software_proxy():
    client = AsyncWebClient(
        timeout=5,
        proxy="http://10.0.0.8:7890",
        cf_bypass_url="http://127.0.0.1:8191",
    )

    assert client._resolve_flaresolverr_proxy(use_proxy=True) == "http://10.0.0.8:7890"
    assert client._resolve_flaresolverr_proxy(use_proxy=False) == ""


def test_flaresolverr_proxy_prefers_dedicated_bypass_proxy():
    client = AsyncWebClient(
        timeout=5,
        proxy="http://10.0.0.8:7890",
        cf_bypass_url="http://127.0.0.1:8191",
        cf_bypass_proxy="http://10.0.0.9:7890",
    )

    assert client._resolve_flaresolverr_proxy(use_proxy=True) == "http://10.0.0.9:7890"


@pytest.mark.asyncio
async def test_flaresolverr_proxy_log_never_exposes_credentials():
    logs: list[str] = []
    client = AsyncWebClient(
        timeout=5,
        proxy="http://user:secret-password@10.0.0.8:7890",
        cf_bypass_url="http://127.0.0.1:8191",
        log_fn=logs.append,
    )

    async def fake_request(*args, **kwargs):
        solution = {"status": "ok", "solution": {"status": 200, "response": "<html>ok</html>"}}
        return _fake_response(status_code=200, content=json.dumps(solution).encode()), ""

    client.request = fake_request  # type: ignore[method-assign]
    response, error = await client._call_flaresolverr("https://example.com", cookies=None, use_proxy=True)

    assert response is not None and error == ""
    joined = "\n".join(logs)
    assert "secret-password" not in joined
    assert "user:" not in joined


@pytest.mark.asyncio
async def test_detect_cf_bypass_service_does_not_cache_transient_failure():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8191")
    calls = 0

    async def fake_request(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None, "temporary failure"
        payload = json.dumps({"msg": "FlareSolverr is ready!"}).encode()
        return _fake_response(status_code=200, content=payload), ""

    client.request = fake_request  # type: ignore[method-assign]

    assert await client._detect_cf_bypass_service() == "mdcx"
    assert client._cf_bypass_service_mode is None
    assert await client._detect_cf_bypass_service() == "flaresolverr"
    assert calls == 2


@pytest.mark.asyncio
async def test_request_preserves_explicit_no_proxy_for_cf_bypass():
    client = AsyncWebClient(
        timeout=1,
        proxy="http://10.0.0.8:7890",
        cf_bypass_url="http://127.0.0.1:8191",
    )
    captured: list[bool] = []

    async def fake_curl_request(**kwargs):
        return _fake_response(
            status_code=403,
            headers={"server": "cloudflare", "content-type": "text/html"},
            content=b"<html>Just a moment <div class='cf-chl'></div></html>",
        )

    async def fake_try_bypass(**kwargs):
        captured.append(kwargs["use_proxy"])
        return _fake_response(status_code=200, content=b"ok"), ""

    client._curl_request = fake_curl_request  # type: ignore[method-assign]
    client._try_bypass_cloudflare = fake_try_bypass  # type: ignore[method-assign]
    response, error = await client.request("GET", "https://example.com", use_proxy=False, retry_count=1)

    assert response is not None and error == ""
    assert captured == [False]


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_uses_flaresolverr_when_detected():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8191")
    calls: list[tuple[str, object]] = []

    async def fake_detect():
        return "flaresolverr"

    async def fake_flaresolverr(target_url, *, cookies, use_proxy):
        calls.append((target_url, cookies))
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    async def unexpected_mirror(**kwargs):
        raise AssertionError("FlareSolverr 模式不应请求 mirror")

    client._detect_cf_bypass_service = fake_detect  # type: ignore[method-assign]
    client._call_flaresolverr = fake_flaresolverr  # type: ignore[method-assign]
    client._call_bypass_mirror = unexpected_mirror  # type: ignore[method-assign]

    response, error = await client._try_bypass_cloudflare(
        host="example.com",
        target_url="https://example.com/challenge",
        cookies={"session": "abc"},
        **{key: value for key, value in _default_try_kwargs().items() if key != "cookies"},
    )

    assert error == ""
    assert response is not None
    assert calls == [("https://example.com/challenge", {"session": "abc"})]


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_throttles_concurrent_attempts_without_failing():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client._cf_bypass_min_interval = 0.02
    host = "missav.ws"

    call_count = 0

    async def fake_call_bypass_mirror(**kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]

    tasks = [
        client._try_bypass_cloudflare(
            host=host,
            target_url="https://missav.ws/SNOS-001/cn",
            **_default_try_kwargs(),
        )
        for _ in range(3)
    ]
    results = await asyncio.gather(*tasks)

    assert call_count == 3
    success_count = sum(1 for response, error in results if response is not None and error == "")
    assert success_count == 3


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_waits_internally_during_cooldown():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client._cf_bypass_min_interval = 0.05
    host = "missav.ws"

    call_count = 0

    async def fake_call_bypass_mirror(**kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]

    first_response, first_error = await client._try_bypass_cloudflare(
        host=host,
        target_url="https://missav.ws/SNOS-002/cn",
        **_default_try_kwargs(),
    )
    start = asyncio.get_running_loop().time()
    second_response, second_error = await client._try_bypass_cloudflare(
        host=host,
        target_url="https://missav.ws/SNOS-002/cn",
        **_default_try_kwargs(),
    )
    elapsed = asyncio.get_running_loop().time() - start

    assert first_error == ""
    assert first_response is not None
    assert second_error == ""
    assert second_response is not None
    assert elapsed >= 0.04
    assert call_count == 2


@pytest.mark.asyncio
async def test_call_bypass_html_uses_html_endpoint_and_params_and_sets_final_url():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    captured: dict[str, object] = {}

    async def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        return (
            _fake_response(
                status_code=200,
                content=b"<html>ok</html>",
                headers={
                    "x-cf-bypasser-final-url": "https://missav.ws/dm2/SNOS-003/cn",
                },
            ),
            "",
        )

    client.request = fake_request  # type: ignore[method-assign]

    response, error = await client._call_bypass_html("https://missav.ws/SNOS-003/cn", use_proxy=False)

    assert error == ""
    assert response is not None
    assert captured["method"] == "GET"
    assert captured["url"] == "http://127.0.0.1:8000/html"
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["params"] == {"url": "https://missav.ws/SNOS-003/cn"}
    assert kwargs["enable_cf_bypass"] is False
    assert response.url == "https://missav.ws/dm2/SNOS-003/cn"
    assert response.headers.get("x-mdcx-bypass-mode") == "html"


@pytest.mark.asyncio
async def test_call_bypass_html_appends_proxy_param_when_configured():
    client = AsyncWebClient(
        timeout=1,
        cf_bypass_url="http://127.0.0.1:8000",
        cf_bypass_proxy="http://127.0.0.1:7890",
    )
    captured: dict[str, object] = {}

    async def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _fake_response(status_code=200, content=b"<html>ok</html>", headers={}), ""

    client.request = fake_request  # type: ignore[method-assign]

    response, error = await client._call_bypass_html("https://missav.ws/SNOS-010/cn", use_proxy=True)

    assert error == ""
    assert response is not None
    assert captured["method"] == "GET"
    assert captured["url"] == "http://127.0.0.1:8000/html"
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["params"] == {
        "url": "https://missav.ws/SNOS-010/cn",
        "proxy": "http://127.0.0.1:7890",
    }
    assert kwargs["use_proxy"] is False
    assert kwargs["enable_cf_bypass"] is False


@pytest.mark.asyncio
async def test_call_bypass_html_appends_bypass_cache_param_when_forced():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    captured: dict[str, object] = {}

    async def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _fake_response(status_code=200, content=b"<html>ok</html>", headers={}), ""

    client.request = fake_request  # type: ignore[method-assign]

    response, error = await client._call_bypass_html(
        "https://missav.ws/SNOS-013/cn",
        use_proxy=False,
        bypass_cache=True,
    )

    assert error == ""
    assert response is not None
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["params"] == {
        "url": "https://missav.ws/SNOS-013/cn",
        "bypassCookieCache": "true",
    }


@pytest.mark.asyncio
async def test_call_bypass_mirror_returns_error_on_http_status():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")

    async def fake_request(method, url, **kwargs):
        return _fake_response(status_code=404, headers={"Content-Type": "text/html"}, content=b"not found")

    _patch_session_request(client, fake_request)

    response, error = await client._call_bypass_mirror(
        method="GET",
        target_url="https://missav.ws/SNOS-404/cn",
        headers={"Accept": "text/html"},
        cookies=None,
        use_proxy=False,
        allow_redirects=True,
    )

    assert response is None
    assert error == "mirror HTTP 404"


@pytest.mark.asyncio
async def test_call_bypass_mirror_follows_redirect_and_updates_final_url():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    captured_calls: list[tuple[str, dict[str, str]]] = []

    async def fake_request(method, url, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        captured_calls.append((url, headers))
        if url.endswith("/hmgl-183/cn") and "/dm18/" not in url:
            return _fake_response(
                status_code=301,
                headers={"Location": "https://missav.ws/dm18/hmgl-183/cn", "Content-Type": "text/html"},
                content=b"",
            )
        return _fake_response(status_code=200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    _patch_session_request(client, fake_request)

    response, error = await client._call_bypass_mirror(
        method="GET",
        target_url="https://missav.ws//hmgl-183/cn",
        headers={"Accept": "text/html"},
        cookies={"sessionid": "abc"},
        use_proxy=False,
        allow_redirects=True,
    )

    assert error == ""
    assert response is not None
    assert len(captured_calls) == 2
    assert captured_calls[0][0] == "http://127.0.0.1:8000/hmgl-183/cn"
    assert captured_calls[1][0] == "http://127.0.0.1:8000/dm18/hmgl-183/cn"
    assert captured_calls[0][1].get("x-hostname") == "missav.ws"
    assert "sessionid=abc" in captured_calls[0][1].get("Cookie", "")
    assert response.url == "https://missav.ws/dm18/hmgl-183/cn"
    assert response.headers.get("x-mdcx-bypass-mode") == "mirror"


@pytest.mark.asyncio
async def test_call_bypass_mirror_sets_x_proxy_header_when_enabled():
    client = AsyncWebClient(
        timeout=1,
        cf_bypass_url="http://127.0.0.1:8000",
        cf_bypass_proxy="http://127.0.0.1:7890",
    )
    captured_headers: dict[str, str] = {}

    async def fake_request(method, url, **kwargs):
        nonlocal captured_headers
        captured_headers = dict(kwargs.get("headers") or {})
        return _fake_response(status_code=200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    _patch_session_request(client, fake_request)

    response, error = await client._call_bypass_mirror(
        method="GET",
        target_url="https://missav.ws/SNOS-011/cn",
        headers={"Accept": "text/html"},
        cookies=None,
        use_proxy=True,
        allow_redirects=True,
    )

    assert error == ""
    assert response is not None
    assert captured_headers.get("x-hostname") == "missav.ws"
    assert captured_headers.get("x-proxy") == "http://127.0.0.1:7890"


@pytest.mark.asyncio
async def test_call_bypass_mirror_sets_x_bypass_cache_header_when_forced():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    captured_headers: dict[str, str] = {}

    async def fake_request(method, url, **kwargs):
        nonlocal captured_headers
        captured_headers = dict(kwargs.get("headers") or {})
        return _fake_response(status_code=200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    _patch_session_request(client, fake_request)

    response, error = await client._call_bypass_mirror(
        method="GET",
        target_url="https://missav.ws/SNOS-014/cn",
        headers={"Accept": "text/html"},
        cookies=None,
        use_proxy=False,
        bypass_cache=True,
        allow_redirects=True,
    )

    assert error == ""
    assert response is not None
    assert captured_headers.get("x-bypass-cache") == "true"


@pytest.mark.asyncio
async def test_call_bypass_mirror_resets_pool_on_transport_error(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    reset_keys: list[str] = []

    async def fake_request(method, url, **kwargs):
        raise Timeout("timed out")

    _patch_session_request(client, fake_request)

    async def fake_reset_connections(reason: str, *, pool_key: str | None = None):
        reset_keys.append(pool_key or "")

    monkeypatch.setattr(client, "reset_connections", fake_reset_connections)

    response, error = await client._call_bypass_mirror(
        method="GET",
        target_url="https://missav.ws/SNOS-014/cn",
        headers={"Accept": "text/html"},
        cookies=None,
        use_proxy=False,
        allow_redirects=True,
    )

    assert response is None
    assert error == "mirror 请求超时"
    assert reset_keys == ["http://127.0.0.1:8000|proxy="]


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_fallbacks_to_html_when_mirror_failed():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")

    mirror_call_count = 0
    html_call_count = 0

    async def fake_call_bypass_mirror(**kwargs):
        nonlocal mirror_call_count
        mirror_call_count += 1
        return None, "mirror failed"

    async def fake_call_bypass_html(target_url: str, *, use_proxy: bool, bypass_cache: bool = False):
        nonlocal html_call_count
        html_call_count += 1
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]
    client._call_bypass_html = fake_call_bypass_html  # type: ignore[method-assign]

    response, error = await client._try_bypass_cloudflare(
        host="missav.ws",
        target_url="https://missav.ws/SNOS-005/cn",
        **_default_try_kwargs(),
    )

    assert error == ""
    assert response is not None
    assert mirror_call_count == 1
    assert html_call_count == 1


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_force_refresh_mirror_before_html_fallback():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    mirror_bypass_cache_flags: list[bool] = []
    html_bypass_cache_flags: list[bool] = []

    async def fake_call_bypass_mirror(**kwargs):
        mirror_bypass_cache_flags.append(bool(kwargs.get("bypass_cache")))
        return None, "mirror 返回 Cloudflare 挑战页"

    async def fake_call_bypass_html(target_url: str, *, use_proxy: bool, bypass_cache: bool = False):
        html_bypass_cache_flags.append(bypass_cache)
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]
    client._call_bypass_html = fake_call_bypass_html  # type: ignore[method-assign]

    response, error = await client._try_bypass_cloudflare(
        host="javdb.com",
        target_url="https://javdb.com/search?q=SNOS-040&locale=zh",
        **_default_try_kwargs(),
    )

    assert error == ""
    assert response is not None
    assert mirror_bypass_cache_flags == [False, True]
    assert html_bypass_cache_flags == [False]


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_skips_html_fallback_for_terminal_mirror_http_status():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")

    mirror_call_count = 0
    html_call_count = 0

    async def fake_call_bypass_mirror(**kwargs):
        nonlocal mirror_call_count
        mirror_call_count += 1
        return None, "mirror HTTP 404"

    async def fake_call_bypass_html(target_url: str, *, use_proxy: bool, bypass_cache: bool = False):
        nonlocal html_call_count
        html_call_count += 1
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]
    client._call_bypass_html = fake_call_bypass_html  # type: ignore[method-assign]

    response, error = await client._try_bypass_cloudflare(
        host="missav.ws",
        target_url="https://missav.ws/SNOS-404/cn",
        **_default_try_kwargs(),
    )

    assert response is None
    assert "mirror 返回终态 HTTP 404，跳过 /html 回退" in error
    assert mirror_call_count == 1
    assert html_call_count == 0


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_non_get_does_not_fallback_to_html():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client._cf_bypass_retries = 1

    async def fake_call_bypass_mirror(**kwargs):
        return None, "mirror failed"

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]

    response, error = await client._try_bypass_cloudflare(
        host="missav.ws",
        method="HEAD",
        target_url="https://missav.ws/SNOS-006/cn",
        headers={},
        cookies=None,
        data=None,
        json_data=None,
        timeout=None,
        allow_redirects=True,
        use_proxy=False,
    )

    assert response is None
    assert "HEAD 不支持 /html 兜底" in error


@pytest.mark.asyncio
async def test_try_bypass_cloudflare_second_retry_forces_bypass_cache():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client._cf_bypass_retries = 2

    bypass_cache_flags: list[bool] = []

    async def fake_call_bypass_mirror(**kwargs):
        bypass_cache_flags.append(bool(kwargs.get("bypass_cache")))
        if len(bypass_cache_flags) == 1:
            return None, "mirror failed"
        return _fake_response(status_code=200, content=b"<html>ok</html>"), ""

    client._call_bypass_mirror = fake_call_bypass_mirror  # type: ignore[method-assign]

    response, error = await client._try_bypass_cloudflare(
        host="missav.ws",
        method="HEAD",
        target_url="https://missav.ws/SNOS-015/cn",
        headers={},
        cookies=None,
        data=None,
        json_data=None,
        timeout=None,
        allow_redirects=True,
        use_proxy=False,
    )

    assert error == ""
    assert response is not None
    assert bypass_cache_flags == [False, True]


@pytest.mark.asyncio
async def test_request_returns_bypass_response_when_cf_challenge_hit():
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    host = "missav.ws"

    call_count = 0

    async def fake_curl_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(
            status_code=503,
            headers={"Content-Type": "text/html", "server": "cloudflare", "cf-ray": "abc"},
            content=b"<html>just a moment cf-chl</html>",
        )

    _patch_session_request(client, fake_curl_request)

    bypass_response = _fake_response(
        status_code=200,
        headers={"Content-Type": "text/html", "x-mdcx-bypass-mode": "mirror"},
        content=b"<html>bypass</html>",
    )

    async def fake_try_bypass_cloudflare(**kwargs):
        return bypass_response, ""

    client._try_bypass_cloudflare = fake_try_bypass_cloudflare  # type: ignore[method-assign]

    response, error = await client.request("GET", f"https://{host}/SNOS-007/cn")

    assert error == ""
    assert response is bypass_response
    assert call_count == 1


@pytest.mark.asyncio
async def test_request_enables_bypass_proxy_when_configured():
    client = AsyncWebClient(
        timeout=1,
        cf_bypass_url="http://127.0.0.1:8000",
        cf_bypass_proxy="http://127.0.0.1:7890",
    )
    host = "missav.ws"

    async def fake_curl_request(method, url, **kwargs):
        return _fake_response(
            status_code=503,
            headers={"Content-Type": "text/html", "server": "cloudflare", "cf-ray": "abc"},
            content=b"<html>just a moment cf-chl</html>",
        )

    _patch_session_request(client, fake_curl_request)

    captured_use_proxy: bool | None = None
    bypass_response = _fake_response(
        status_code=200,
        headers={"Content-Type": "text/html", "x-mdcx-bypass-mode": "mirror"},
        content=b"<html>bypass</html>",
    )

    async def fake_try_bypass_cloudflare(**kwargs):
        nonlocal captured_use_proxy
        captured_use_proxy = kwargs.get("use_proxy")
        return bypass_response, ""

    client._try_bypass_cloudflare = fake_try_bypass_cloudflare  # type: ignore[method-assign]

    response, error = await client.request("GET", f"https://{host}/SNOS-012/cn")

    assert error == ""
    assert response is bypass_response
    assert captured_use_proxy is True


@pytest.mark.asyncio
async def test_request_retries_when_bypass_failed(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client.retry = 2
    host = "missav.ws"

    async def fake_try_bypass_cloudflare(**kwargs):
        return None, "bypass cooling down"

    client._try_bypass_cloudflare = fake_try_bypass_cloudflare  # type: ignore[method-assign]

    call_count = 0

    async def fake_curl_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _fake_response(
                status_code=503,
                headers={"Content-Type": "text/html", "server": "cloudflare", "cf-ray": "abc"},
                content=b"<html>just a moment cf-chl</html>",
            )
        return _fake_response(
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"ok",
        )

    _patch_session_request(client, fake_curl_request)

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.5)

    response, error = await client.request("GET", f"https://{host}/SNOS-008/cn")

    assert error == ""
    assert response is not None
    assert call_count == 2
    assert sleep_calls == [2.5]


@pytest.mark.asyncio
async def test_request_stops_retry_when_bypass_failed_with_terminal_status(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client.retry = 5
    host = "missav.ws"

    async def fake_try_bypass_cloudflare(**kwargs):
        return None, "mirror 返回终态 HTTP 404，跳过 /html 回退"

    client._try_bypass_cloudflare = fake_try_bypass_cloudflare  # type: ignore[method-assign]

    call_count = 0

    async def fake_curl_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(
            status_code=503,
            headers={"Content-Type": "text/html", "server": "cloudflare", "cf-ray": "abc"},
            content=b"<html>just a moment cf-chl</html>",
        )

    _patch_session_request(client, fake_curl_request)

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    response, error = await client.request("GET", f"https://{host}/SNOS-404/cn")

    assert response is None
    assert "终态 HTTP 404" in error
    assert call_count == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_request_stops_retry_when_bypass_failed_with_http_terminal_status(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="http://127.0.0.1:8000")
    client.retry = 5
    host = "missav.ws"

    async def fake_try_bypass_cloudflare(**kwargs):
        return None, "HTTP 404"

    client._try_bypass_cloudflare = fake_try_bypass_cloudflare  # type: ignore[method-assign]

    call_count = 0

    async def fake_curl_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(
            status_code=503,
            headers={"Content-Type": "text/html", "server": "cloudflare", "cf-ray": "abc"},
            content=b"<html>just a moment cf-chl</html>",
        )

    _patch_session_request(client, fake_curl_request)

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    response, error = await client.request("GET", f"https://{host}/SNOS-404/cn")

    assert response is None
    assert "HTTP 404" in error
    assert call_count == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_request_acquires_limiter_for_each_attempt(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="")
    client.retry = 3

    acquire_count = 0

    class FakeLimiter:
        async def acquire(self):
            nonlocal acquire_count
            acquire_count += 1

    class FakeLimiters:
        def get(self, key):
            return FakeLimiter()

    client.limiters = FakeLimiters()  # type: ignore[assignment]

    call_count = 0

    async def fake_curl_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(
            status_code=503,
            headers={"Content-Type": "text/html"},
            content=b"busy",
        )

    _patch_session_request(client, fake_curl_request)

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.0)

    response, error = await client.request("GET", "https://missav.ws/SNOS-009/cn")

    assert response is None
    assert "HTTP 503" in error
    assert call_count == 3
    assert acquire_count == 3
    assert sleep_calls == [2.0, 5.0]


@pytest.mark.asyncio
async def test_request_does_not_use_cf_retry_semaphore_before_challenge(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="")

    async def fail_if_called(host: str):
        raise AssertionError("普通请求不应默认使用 CF retry semaphore")

    monkeypatch.setattr(client, "_get_cf_host_retry_semaphore", fail_if_called)
    _patch_session_request(
        client,
        lambda method, url, **kwargs: _fake_response(
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"ok",
        ),
    )

    response, error = await client.request("GET", "https://missav.ws/SNOS-009/cn")

    assert error == ""
    assert response is not None


@pytest.mark.asyncio
async def test_request_uses_cf_retry_semaphore_after_challenge(monkeypatch):
    client = AsyncWebClient(timeout=1, cf_bypass_url="")
    client._cf_host_challenge_hits["missav.ws"] = 1
    enter_count = 0

    class FakeSemaphore:
        async def __aenter__(self):
            nonlocal enter_count
            enter_count += 1

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_get_semaphore(host: str):
        return FakeSemaphore()

    monkeypatch.setattr(client, "_get_cf_host_retry_semaphore", fake_get_semaphore)
    _patch_session_request(
        client,
        lambda method, url, **kwargs: _fake_response(
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"ok",
        ),
    )

    response, error = await client.request("GET", "https://missav.ws/SNOS-009/cn")

    assert error == ""
    assert response is not None
    assert enter_count == 1


def test_sanitize_url_keeps_query_and_encodes_spaces():
    client = AsyncWebClient(timeout=1)
    url = "https://api.theporndb.net/movies?q=blacked ARIA LEE&per_page=100"

    sanitized_url, sanitized = client._sanitize_url(url)

    assert sanitized is True
    assert sanitized_url == "https://api.theporndb.net/movies?q=blacked%20ARIA%20LEE&per_page=100"


def test_sanitize_url_still_removes_polluted_suffix():
    client = AsyncWebClient(timeout=1)
    url = 'https://x.com?a=1">https://x.com?a=1'

    sanitized_url, sanitized = client._sanitize_url(url)

    assert sanitized is True
    assert sanitized_url == "https://x.com?a=1"
