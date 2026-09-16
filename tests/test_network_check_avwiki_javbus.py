from types import SimpleNamespace

from mdcx.config.enums import Website
from mdcx.core import network_check as module
from mdcx.core.network_check import NetworkCheckSpec, NetworkCheckStatus


def test_static_network_checks_include_avwiki(monkeypatch):
    config = SimpleNamespace(
        use_proxy=False,
        proxy="",
        cf_bypass_url="",
        cf_bypass_proxy="",
        theporndb_api_token="",
    )
    monkeypatch.setattr(module, "_manager", lambda: SimpleNamespace(config=config))

    specs = module._build_static_specs()
    avwiki = next(spec for spec in specs if spec.name == "av-wiki")

    assert avwiki.group == "刮削站点"
    assert avwiki.url == module.AVWIKI_CHECK_URL
    assert avwiki.enable_cf_bypass is True


def test_javbus_reports_valid_cookie_after_authenticated_page(monkeypatch):
    monkeypatch.setattr(module, "_is_cloudflare_challenge", lambda _text: False)
    spec = NetworkCheckSpec(
        name="javbus",
        group="刮削站点",
        url="https://www.javbus.com/FSDSS-660",
        site=Website.JAVBUS,
        headers={"cookie": "session=valid"},
    )

    status, message = module._classify_http_result(spec, 200, "<html><body>movie page</body></html>")

    assert status == NetworkCheckStatus.OK
    assert message == "连接正常，Cookie 有效"


def test_javbus_still_warns_when_cookie_does_not_authenticate(monkeypatch):
    monkeypatch.setattr(module, "_is_cloudflare_challenge", lambda _text: False)
    spec = NetworkCheckSpec(
        name="javbus",
        group="刮削站点",
        url="https://www.javbus.com/FSDSS-660",
        site=Website.JAVBUS,
        headers={"cookie": "session=expired"},
    )

    status, message = module._classify_http_result(spec, 200, "lostpasswd")

    assert status == NetworkCheckStatus.WARNING
    assert "Cookie 可能无效" in message
