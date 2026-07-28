import asyncio

import pytest

from mdcx.auth.fc2cmadb_session import (
    FC2CMADBAuthenticationError,
    FC2CMADBSessionManager,
    FC2CMADBValidationUnavailable,
    is_fc2cmadb_authentication_failure,
)


class FakeConfig:
    fc2ppvdb = "old-cookie"
    fc2cmadb_auth_mode = "auto"


class FakeConfigManager:
    def __init__(self):
        self.config = FakeConfig()


class FakeAuthManager:
    def __init__(self, config_manager, *, validation=(True, "")):
        self.config_manager = config_manager
        self.validation = validation
        self.login_calls = 0
        self.validation_calls = 0

    def get_cookie(self):
        return self.config_manager.config.fc2ppvdb

    async def validate_cookie(self, _cookie):
        self.validation_calls += 1
        return self.validation

    async def login(self, username, password):
        assert (username, password) == ("test-user", "runtime-password")
        self.login_calls += 1
        self.config_manager.config.fc2ppvdb = "new-cookie"
        return "new-cookie"


def test_login_page_response_is_recognized_as_fc2cmadb_authentication_failure():
    error = "详情页跳转到登录页，fc2cmadb Cookie 未生效: https://fc2cmadb.com/login"

    assert is_fc2cmadb_authentication_failure(error) is True


def test_cloudflare_403_is_not_fc2cmadb_authentication_failure():
    assert is_fc2cmadb_authentication_failure("详情页请求失败: HTTP 403 (Cloudflare challenge)") is False


@pytest.mark.parametrize(
    "error",
    (
        "详情页请求失败: HTTP 403",
        "详情页请求失败: HTTP 404",
        "详情页请求失败: timeout",
        "详情页请求失败: network unreachable",
    ),
)
def test_non_authentication_failures_do_not_expire_fc2cmadb_cookie(error):
    assert is_fc2cmadb_authentication_failure(error) is False


def test_http_401_is_recognized_as_fc2cmadb_authentication_failure():
    assert is_fc2cmadb_authentication_failure("详情页请求失败: HTTP 401") is True


@pytest.mark.asyncio
async def test_automatic_refresh_uses_runtime_credentials_and_returns_new_cookie():
    config_manager = FakeConfigManager()
    auth_manager = FakeAuthManager(config_manager)
    session = FC2CMADBSessionManager(
        config_manager=config_manager,
        auth_manager=auth_manager,
        credentials_getter=lambda: ("test-user", "runtime-password"),
    )

    cookie = await session.recover_after_authentication_failure("old-cookie")

    assert cookie == "new-cookie"
    assert auth_manager.login_calls == 1


@pytest.mark.asyncio
async def test_cloudflare_preflight_failure_does_not_trigger_automatic_refresh():
    config_manager = FakeConfigManager()
    auth_manager = FakeAuthManager(
        config_manager,
        validation=(False, "暂时无法验证登录状态：详情页请求失败: HTTP 403"),
    )
    session = FC2CMADBSessionManager(
        config_manager=config_manager,
        auth_manager=auth_manager,
        credentials_getter=lambda: ("test-user", "runtime-password"),
    )

    with pytest.raises(FC2CMADBValidationUnavailable, match="HTTP 403"):
        await session.ensure_cookie_valid()

    assert auth_manager.login_calls == 0


@pytest.mark.asyncio
async def test_one_scrape_session_attempts_browser_refresh_at_most_once():
    config_manager = FakeConfigManager()
    auth_manager = FakeAuthManager(config_manager)
    session = FC2CMADBSessionManager(
        config_manager=config_manager,
        auth_manager=auth_manager,
        credentials_getter=lambda: ("test-user", "runtime-password"),
    )

    assert await session.recover_after_authentication_failure("old-cookie") == "new-cookie"

    with pytest.raises(FC2CMADBAuthenticationError, match="已经刷新一次"):
        await session.recover_after_authentication_failure("new-cookie")

    assert auth_manager.login_calls == 1


@pytest.mark.asyncio
async def test_concurrent_authentication_failures_share_one_browser_login():
    config_manager = FakeConfigManager()

    class BlockingAuthManager(FakeAuthManager):
        def __init__(self, config_manager):
            super().__init__(config_manager)
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def login(self, username, password):
            self.login_calls += 1
            self.started.set()
            await self.release.wait()
            self.config_manager.config.fc2ppvdb = "new-cookie"
            return "new-cookie"

    auth_manager = BlockingAuthManager(config_manager)
    session = FC2CMADBSessionManager(
        config_manager=config_manager,
        auth_manager=auth_manager,
        credentials_getter=lambda: ("test-user", "runtime-password"),
    )

    first = asyncio.create_task(session.recover_after_authentication_failure("old-cookie"))
    await auth_manager.started.wait()
    waiters = [asyncio.create_task(session.recover_after_authentication_failure("old-cookie")) for _ in range(4)]
    await asyncio.sleep(0)

    assert auth_manager.login_calls == 1
    assert all(not waiter.done() for waiter in waiters)

    auth_manager.release.set()
    results = await asyncio.gather(first, *waiters)

    assert results == ["new-cookie"] * 5
    assert auth_manager.login_calls == 1


@pytest.mark.asyncio
async def test_preflight_refreshes_definitively_expired_cookie_once():
    config_manager = FakeConfigManager()
    auth_manager = FakeAuthManager(
        config_manager,
        validation=(False, "Cookie 无效或已过期：登录后影片访问失败（HTTP 404）"),
    )
    session = FC2CMADBSessionManager(
        config_manager=config_manager,
        auth_manager=auth_manager,
        credentials_getter=lambda: ("test-user", "runtime-password"),
    )

    await session.ensure_cookie_valid()
    await session.ensure_cookie_valid()

    assert auth_manager.validation_calls == 1
    assert auth_manager.login_calls == 1
    assert config_manager.config.fc2ppvdb == "new-cookie"


@pytest.mark.asyncio
async def test_manual_mode_preflight_requests_cookie_update_without_login():
    config_manager = FakeConfigManager()
    config_manager.config.fc2cmadb_auth_mode = "manual"
    auth_manager = FakeAuthManager(
        config_manager,
        validation=(False, "Cookie 无效或已过期：缺少 fc2cmadb-session"),
    )
    session = FC2CMADBSessionManager(config_manager=config_manager, auth_manager=auth_manager)

    with pytest.raises(FC2CMADBAuthenticationError, match="更新手动 Cookie"):
        await session.ensure_cookie_valid()

    assert auth_manager.login_calls == 0


@pytest.mark.asyncio
async def test_automatic_refresh_failure_is_reported_and_not_retried():
    config_manager = FakeConfigManager()

    class FailingAuthManager(FakeAuthManager):
        async def login(self, username, password):
            self.login_calls += 1
            raise RuntimeError("browser login failed")

    auth_manager = FailingAuthManager(config_manager)
    session = FC2CMADBSessionManager(
        config_manager=config_manager,
        auth_manager=auth_manager,
        credentials_getter=lambda: ("test-user", "runtime-password"),
    )

    with pytest.raises(FC2CMADBAuthenticationError, match="自动刷新失败"):
        await session.recover_after_authentication_failure("old-cookie")
    with pytest.raises(FC2CMADBAuthenticationError, match="自动刷新失败"):
        await session.recover_after_authentication_failure("old-cookie")

    assert auth_manager.login_calls == 1
    assert config_manager.config.fc2ppvdb == "old-cookie"
