import pytest

from mdcx.auth.fc2cmadb import FC2CMADBAuthError, FC2CMADBAuthManager


class FakeConfig:
    fc2ppvdb = "old-cookie"
    use_proxy = False


class FakeConfigManager:
    def __init__(self):
        self.config = FakeConfig()
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
