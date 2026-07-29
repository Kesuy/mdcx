import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcx.auth.fc2cmadb import FC2CMADBAuthError, FC2CMADBAuthManager, PlaywrightUnavailableError


class FakeConfig:
    fc2ppvdb = "old-cookie"
    use_proxy = False
    proxy = "http://127.0.0.1:7890"


class FakeConfigManager:
    def __init__(self):
        self.config = FakeConfig()
        self.data_folder = Path("runtime-data")
        self.save_calls = 0

    def save(self):
        self.save_calls += 1


@pytest.mark.asyncio
async def test_login_saves_valid_playwright_cookie():
    config_manager = FakeConfigManager()
    validation_calls = []

    async def browser_login(username, password):
        assert username == "test-user"
        assert password == "runtime-password"
        return [
            {"name": "fc2cmadb-session", "value": "new-session"},
            {"name": "ageVerified", "value": "true"},
        ]

    async def validate(cookie):
        validation_calls.append(cookie)
        return True, ""

    auth = FC2CMADBAuthManager(
        config_manager=config_manager,
        browser_login=browser_login,
        cookie_validator=validate,
    )

    cookie = await auth.login("test-user", "runtime-password")

    assert cookie == "fc2cmadb-session=new-session; ageVerified=true"
    assert validation_calls == [cookie]
    assert config_manager.config.fc2ppvdb == cookie
    assert config_manager.save_calls == 1
    assert auth.get_cookie() == cookie


@pytest.mark.asyncio
async def test_login_failure_preserves_existing_cookie():
    config_manager = FakeConfigManager()

    async def browser_login(_username, _password):
        raise FC2CMADBAuthError("登录失败")

    auth = FC2CMADBAuthManager(config_manager=config_manager, browser_login=browser_login)

    with pytest.raises(FC2CMADBAuthError, match="登录失败"):
        await auth.login("test-user", "runtime-password")

    assert config_manager.config.fc2ppvdb == "old-cookie"
    assert config_manager.save_calls == 0


@pytest.mark.asyncio
async def test_invalid_cookie_preserves_existing_cookie():
    config_manager = FakeConfigManager()

    async def browser_login(_username, _password):
        return [{"name": "fc2cmadb-session", "value": "invalid-session"}]

    async def validate(_cookie):
        return False, "Cookie 无效或已过期"

    auth = FC2CMADBAuthManager(
        config_manager=config_manager,
        browser_login=browser_login,
        cookie_validator=validate,
    )

    with pytest.raises(FC2CMADBAuthError, match="Cookie 无效或已过期"):
        await auth.login("test-user", "runtime-password")

    assert config_manager.config.fc2ppvdb == "old-cookie"
    assert config_manager.save_calls == 0


def test_manager_initialization_does_not_start_playwright():
    config_manager = FakeConfigManager()
    browser_calls = []

    async def browser_login(_username, _password):
        browser_calls.append(True)
        return []

    auth = FC2CMADBAuthManager(config_manager=config_manager, browser_login=browser_login)

    assert auth.get_cookie() == "old-cookie"
    assert browser_calls == []


@pytest.mark.asyncio
async def test_installed_browser_launcher_prefers_microsoft_edge():
    launch_calls = []
    expected_browser = object()

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return expected_browser

    browser = await FC2CMADBAuthManager._launch_installed_browser(FakeChromium())

    assert browser is expected_browser
    assert launch_calls == [{"channel": "msedge", "headless": False}]


@pytest.mark.asyncio
async def test_persistent_browser_launcher_reuses_dedicated_profile():
    launch_calls = []
    expected_context = object()

    class FakeChromium:
        async def launch_persistent_context(self, user_data_dir, **kwargs):
            launch_calls.append((user_data_dir, kwargs))
            return expected_context

    profile_dir = Path("runtime-data") / ".fc2cmadb-browser"
    context = await FC2CMADBAuthManager._launch_persistent_browser_context(
        FakeChromium(),
        profile_dir,
    )

    assert context is expected_context
    assert launch_calls == [
        (
            str(profile_dir),
            {
                "channel": "msedge",
                "headless": False,
                "no_viewport": True,
                "ignore_default_args": ["--enable-automation"],
            },
        )
    ]


@pytest.mark.asyncio
async def test_persistent_browser_launcher_falls_back_to_chrome():
    launch_calls = []
    expected_context = object()

    class FakeChromium:
        async def launch_persistent_context(self, user_data_dir, **kwargs):
            launch_calls.append((user_data_dir, kwargs))
            if kwargs["channel"] == "msedge":
                raise RuntimeError("Chromium distribution 'msedge' is not found")
            return expected_context

    profile_dir = Path("runtime-data") / ".fc2cmadb-browser"
    context = await FC2CMADBAuthManager._launch_persistent_browser_context(
        FakeChromium(),
        profile_dir,
        "http://proxy.example:8080",
    )

    assert context is expected_context
    assert [options["channel"] for _path, options in launch_calls] == ["msedge", "chrome"]
    assert all(path == str(profile_dir) for path, _options in launch_calls)
    assert all(options["proxy"] == {"server": "http://proxy.example:8080"} for _path, options in launch_calls)


@pytest.mark.asyncio
async def test_persistent_browser_launcher_does_not_hide_launch_failure():
    class FakeChromium:
        async def launch_persistent_context(self, _user_data_dir, **_kwargs):
            raise RuntimeError("browser process crashed: policy denied")

    with pytest.raises(RuntimeError, match="policy denied"):
        await FC2CMADBAuthManager._launch_persistent_browser_context(
            FakeChromium(),
            Path("runtime-data") / ".fc2cmadb-browser",
        )


@pytest.mark.asyncio
async def test_persistent_browser_launcher_reports_when_edge_and_chrome_are_missing():
    class FakeChromium:
        async def launch_persistent_context(self, _user_data_dir, **kwargs):
            raise RuntimeError(f"Chromium distribution '{kwargs['channel']}' is not found")

    with pytest.raises(PlaywrightUnavailableError, match="Microsoft Edge 或 Google Chrome"):
        await FC2CMADBAuthManager._launch_persistent_browser_context(
            FakeChromium(),
            Path("runtime-data") / ".fc2cmadb-browser",
        )


@pytest.mark.asyncio
async def test_installed_browser_launcher_falls_back_to_google_chrome():
    launch_calls = []
    expected_browser = object()

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            if kwargs["channel"] == "msedge":
                raise RuntimeError("Chromium distribution 'msedge' is not found")
            return expected_browser

    browser = await FC2CMADBAuthManager._launch_installed_browser(FakeChromium())

    assert browser is expected_browser
    assert launch_calls == [
        {"channel": "msedge", "headless": False},
        {"channel": "chrome", "headless": False},
    ]


@pytest.mark.asyncio
async def test_installed_browser_launcher_reports_when_edge_and_chrome_are_missing():
    class FakeChromium:
        async def launch(self, **kwargs):
            raise RuntimeError(f"Chromium distribution '{kwargs['channel']}' is not found")

    with pytest.raises(PlaywrightUnavailableError, match="Microsoft Edge 或 Google Chrome"):
        await FC2CMADBAuthManager._launch_installed_browser(FakeChromium())


@pytest.mark.asyncio
async def test_installed_browser_launcher_does_not_hide_non_missing_edge_error():
    launch_calls = []

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            raise RuntimeError("browser process crashed: policy denied")

    with pytest.raises(RuntimeError, match="policy denied"):
        await FC2CMADBAuthManager._launch_installed_browser(FakeChromium())

    assert launch_calls == [{"channel": "msedge", "headless": False}]


@pytest.mark.asyncio
async def test_installed_browser_launcher_passes_plain_proxy():
    launch_calls = []

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return object()

    await FC2CMADBAuthManager._launch_installed_browser(
        FakeChromium(),
        "http://proxy.example:8080",
    )

    assert launch_calls == [
        {
            "channel": "msedge",
            "headless": False,
            "proxy": {"server": "http://proxy.example:8080"},
        }
    ]


@pytest.mark.asyncio
async def test_installed_browser_launcher_passes_plain_socks5h_proxy():
    launch_calls = []

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return object()

    await FC2CMADBAuthManager._launch_installed_browser(
        FakeChromium(),
        "socks5h://proxy.example:1080",
    )

    assert launch_calls == [
        {
            "channel": "msedge",
            "headless": False,
            "proxy": {"server": "socks5h://proxy.example:1080"},
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("scheme", ["socks4", "socks5", "socks5h"])
async def test_installed_browser_launcher_rejects_authenticated_socks_proxy(scheme):
    launch_calls = []

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return object()

    with pytest.raises(FC2CMADBAuthError, match="不支持需要用户名或密码的 SOCKS 代理"):
        await FC2CMADBAuthManager._launch_installed_browser(
            FakeChromium(),
            f"{scheme}://test-user:p%40ssword@proxy.example:1080",
        )

    assert launch_calls == []


@pytest.mark.asyncio
async def test_installed_browser_launcher_splits_authenticated_proxy_credentials():
    launch_calls = []

    class FakeChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return object()

    await FC2CMADBAuthManager._launch_installed_browser(
        FakeChromium(),
        "http://test-user:p%40ssword@proxy.example:8080",
    )

    assert launch_calls == [
        {
            "channel": "msedge",
            "headless": False,
            "proxy": {
                "server": "http://proxy.example:8080",
                "username": "test-user",
                "password": "p@ssword",
            },
        }
    ]


@pytest.mark.asyncio
async def test_browser_login_tells_packaged_users_to_reinstall_when_playwright_is_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "playwright.async_api":
            raise ImportError("missing packaged dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(PlaywrightUnavailableError, match="重新安装 MDCx"):
        await FC2CMADBAuthManager._login_with_playwright("test-user", "runtime-password")


@pytest.mark.asyncio
async def test_browser_login_does_not_expose_proxy_credentials_in_errors(monkeypatch):
    import playwright.async_api as playwright_api

    secret = "proxy-secret"

    class FakePlaywrightContext:
        async def __aenter__(self):
            return SimpleNamespace(chromium=object())

        async def __aexit__(self, *_args):
            return False

    async def fail_launch(_chromium, _user_data_dir, _proxy_server=None):
        raise RuntimeError(f"launch failed with password={secret}")

    monkeypatch.setattr(playwright_api, "async_playwright", FakePlaywrightContext)
    monkeypatch.setattr(FC2CMADBAuthManager, "_launch_persistent_browser_context", fail_launch)

    with pytest.raises(FC2CMADBAuthError) as exc_info:
        await FC2CMADBAuthManager._login_with_playwright(
            "test-user",
            "runtime-password",
            f"http://proxy-user:{secret}@proxy.example:8080",
        )

    assert secret not in str(exc_info.value)


@pytest.mark.asyncio
async def test_default_browser_login_uses_the_configured_proxy(monkeypatch):
    config_manager = FakeConfigManager()
    config_manager.config.use_proxy = True
    browser_calls = []

    async def fake_browser_login(username, password, proxy_server, user_data_dir):
        browser_calls.append((username, password, proxy_server, user_data_dir))
        return [{"name": "fc2cmadb-session", "value": "new-session"}]

    async def validate(_cookie):
        return True, ""

    monkeypatch.setattr(FC2CMADBAuthManager, "_login_with_playwright", fake_browser_login)
    auth = FC2CMADBAuthManager(config_manager=config_manager, cookie_validator=validate)

    await auth.login("test-user", "runtime-password")

    assert browser_calls == [
        (
            "test-user",
            "runtime-password",
            "http://127.0.0.1:7890",
            Path("runtime-data") / ".fc2cmadb-browser",
        )
    ]


@pytest.mark.asyncio
async def test_default_browser_login_omits_disabled_proxy(monkeypatch):
    config_manager = FakeConfigManager()
    browser_calls = []

    async def fake_browser_login(username, password, proxy_server, user_data_dir):
        browser_calls.append((username, password, proxy_server, user_data_dir))
        return [{"name": "fc2cmadb-session", "value": "new-session"}]

    async def validate(_cookie):
        return True, ""

    monkeypatch.setattr(FC2CMADBAuthManager, "_login_with_playwright", fake_browser_login)
    auth = FC2CMADBAuthManager(config_manager=config_manager, cookie_validator=validate)

    await auth.login("test-user", "runtime-password")

    assert browser_calls == [
        (
            "test-user",
            "runtime-password",
            None,
            Path("runtime-data") / ".fc2cmadb-browser",
        )
    ]


@pytest.mark.asyncio
async def test_cloudflare_challenge_waits_for_login_form_before_autofill():
    events = []

    class FakeLocator:
        def __init__(self, kind, page):
            self.kind = kind
            self.page = page
            self.first = self

        async def count(self):
            return int(self.page.elapsed_ms >= 2_000)

        async def fill(self, value):
            events.append(("fill", self.kind, value))
            self.page.values[self.kind] = value

        async def input_value(self):
            return self.page.values.get(self.kind, "")

        async def is_enabled(self):
            return True

        async def click(self):
            events.append(("click", self.kind))
            self.page.url = "https://fc2cmadb.com/"

    class FakeMissingLocator:
        def __init__(self):
            self.first = self

        async def count(self):
            return 0

    class FakePage:
        url = "https://fc2cmadb.com/login"
        elapsed_ms = 0
        values = {}

        def locator(self, selector):
            if "cf-turnstile-response" in selector:
                return FakeMissingLocator()
            if "password" in selector:
                kind = "password"
            elif "submit" in selector:
                kind = "submit"
            else:
                kind = "username"
            return FakeLocator(kind, self)

        def is_closed(self):
            return False

        async def wait_for_timeout(self, timeout_ms):
            self.elapsed_ms += timeout_ms
            events.append(("wait", timeout_ms))

    class FakeContext:
        def __init__(self, page):
            self.page = page

        async def cookies(self):
            if self.page.url.endswith("/login"):
                return [{"name": "fc2cmadb-session", "value": "anonymous"}]
            return [{"name": "fc2cmadb-session", "value": "authenticated"}]

    page = FakePage()
    cookies = await FC2CMADBAuthManager._complete_browser_login(
        page,
        FakeContext(page),
        "test-user",
        "runtime-password",
        timeout_ms=5_000,
    )

    assert events[:2] == [("wait", 1_000), ("wait", 1_000)]
    assert ("fill", "username", "test-user") in events
    assert ("fill", "password", "runtime-password") in events
    assert cookies == [{"name": "fc2cmadb-session", "value": "authenticated"}]


@pytest.mark.asyncio
async def test_login_waits_for_turnstile_token_before_submitting():
    events = []

    class FakeLocator:
        def __init__(self, kind, page):
            self.kind = kind
            self.page = page
            self.first = self

        async def count(self):
            return 1

        async def fill(self, value):
            events.append(("fill", self.kind, value, self.page.elapsed_ms))
            self.page.values[self.kind] = value

        async def input_value(self):
            if self.kind == "turnstile":
                return "verified-token" if self.page.elapsed_ms >= 2_000 else ""
            return self.page.values.get(self.kind, "")

        async def is_enabled(self):
            return self.page.elapsed_ms >= 2_000

        async def click(self):
            events.append(("click", self.kind, self.page.elapsed_ms))
            self.page.url = "https://fc2cmadb.com/"

    class FakePage:
        url = "https://fc2cmadb.com/login"
        elapsed_ms = 0
        values = {}

        def locator(self, selector):
            if "cf-turnstile-response" in selector:
                kind = "turnstile"
            elif "password" in selector:
                kind = "password"
            elif "submit" in selector:
                kind = "submit"
            else:
                kind = "username"
            return FakeLocator(kind, self)

        def is_closed(self):
            return False

        async def wait_for_timeout(self, timeout_ms):
            self.elapsed_ms += timeout_ms
            events.append(("wait", timeout_ms))

    class FakeContext:
        async def cookies(self):
            if page.url.endswith("/login"):
                return []
            return [{"name": "fc2cmadb-session", "value": "authenticated"}]

    page = FakePage()
    await FC2CMADBAuthManager._complete_browser_login(
        page,
        FakeContext(),
        "test-user",
        "runtime-password",
        timeout_ms=5_000,
    )

    submit_events = [event for event in events if event[:2] == ("click", "submit")]
    assert submit_events == [("click", "submit", 2_000)]


@pytest.mark.asyncio
async def test_login_refills_credentials_after_cloudflare_replaces_the_form():
    events = []

    class FakeLocator:
        def __init__(self, kind, page):
            self.kind = kind
            self.page = page
            self.first = self

        async def count(self):
            return 1

        async def fill(self, value):
            events.append(("fill", self.kind, value, self.page.elapsed_ms))
            self.page.values[self.kind] = value

        async def input_value(self):
            if self.kind == "turnstile":
                return "verified-token" if self.page.elapsed_ms >= 2_000 else ""
            return self.page.values.get(self.kind, "")

        async def is_enabled(self):
            return self.page.elapsed_ms >= 2_000

        async def click(self):
            events.append(
                (
                    "click",
                    self.kind,
                    self.page.elapsed_ms,
                    self.page.values.get("username", ""),
                    self.page.values.get("password", ""),
                )
            )
            if self.page.values == {
                "username": "test-user",
                "password": "runtime-password",
            }:
                self.page.url = "https://fc2cmadb.com/"

    class FakePage:
        url = "https://fc2cmadb.com/login"
        elapsed_ms = 0

        def __init__(self):
            self.values = {}

        def locator(self, selector):
            if "cf-turnstile-response" in selector:
                kind = "turnstile"
            elif "password" in selector:
                kind = "password"
            elif "submit" in selector:
                kind = "submit"
            else:
                kind = "username"
            return FakeLocator(kind, self)

        def is_closed(self):
            return False

        async def wait_for_timeout(self, timeout_ms):
            self.elapsed_ms += timeout_ms
            if self.elapsed_ms == 1_000:
                self.values = {}

    class FakeContext:
        async def cookies(self):
            if page.url.endswith("/login"):
                return []
            return [{"name": "fc2cmadb-session", "value": "authenticated"}]

    page = FakePage()
    await FC2CMADBAuthManager._complete_browser_login(
        page,
        FakeContext(),
        "test-user",
        "runtime-password",
        timeout_ms=5_000,
    )

    username_fills = [event for event in events if event[:2] == ("fill", "username")]
    password_fills = [event for event in events if event[:2] == ("fill", "password")]
    submit_events = [event for event in events if event[:2] == ("click", "submit")]
    assert [event[3] for event in username_fills] == [0, 1_000]
    assert [event[3] for event in password_fills] == [0, 1_000]
    assert submit_events == [("click", "submit", 2_000, "test-user", "runtime-password")]
