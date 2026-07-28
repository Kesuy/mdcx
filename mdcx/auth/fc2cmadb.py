from collections.abc import Awaitable, Callable
from typing import Any

from ..config.manager import manager
from ..crawlers.fc2ppvdb import cookie_dict_to_str, validate_fc2cmadb_cookie

BrowserLogin = Callable[[str, str], Awaitable[list[dict[str, Any]]]]
CookieValidator = Callable[[str], Awaitable[tuple[bool, str]]]


class FC2CMADBAuthError(RuntimeError):
    """Raised when FC2CMADB browser authentication cannot produce a valid Cookie."""


class PlaywrightUnavailableError(FC2CMADBAuthError):
    """Raised when optional Playwright browser components are unavailable."""


class FC2CMADBAuthManager:
    def __init__(
        self,
        *,
        config_manager=manager,
        browser_login: BrowserLogin | None = None,
        cookie_validator: CookieValidator | None = None,
    ) -> None:
        self._config_manager = config_manager
        self._browser_login = browser_login or self._login_with_playwright
        self._cookie_validator = cookie_validator

    def get_cookie(self) -> str:
        return self._config_manager.config.fc2ppvdb

    async def validate_cookie(self, cookie: str) -> tuple[bool, str]:
        if self._cookie_validator is not None:
            return await self._cookie_validator(cookie)
        async with self._config_manager.acquire_computed() as computed:
            return await validate_fc2cmadb_cookie(
                computed.async_client,
                cookie,
                use_proxy=self._config_manager.config.use_proxy,
            )

    async def login(self, username: str, password: str) -> str:
        if not username.strip() or not password:
            raise FC2CMADBAuthError("用户名和密码不能为空")

        browser_cookies = await self._browser_login(username.strip(), password)
        cookies = {
            str(cookie.get("name", "")): str(cookie.get("value", ""))
            for cookie in browser_cookies
            if cookie.get("name") and cookie.get("value") is not None
        }
        cookie = cookie_dict_to_str(cookies)
        valid, error = await self.validate_cookie(cookie)
        if not valid:
            raise FC2CMADBAuthError(error or "登录后 Cookie 验证失败")

        self._config_manager.config.fc2ppvdb = cookie
        self._config_manager.save()
        return cookie

    @staticmethod
    async def _login_with_playwright(username: str, password: str) -> list[dict[str, Any]]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PlaywrightUnavailableError("自动登录功能需要安装浏览器组件") from exc

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=False)
                try:
                    context = await browser.new_context()
                    page = await context.new_page()
                    await page.goto("https://fc2cmadb.com/login", wait_until="domcontentloaded")
                    username_input = page.locator(
                        'input[name="email"], input[name="username"], input[type="email"]'
                    ).first
                    await username_input.fill(username)
                    await page.locator('input[name="password"], input[type="password"]').first.fill(password)
                    await page.locator('button[type="submit"], input[type="submit"]').first.click()

                    # Keep the headed browser open so the user can complete a CAPTCHA when one is shown.
                    deadline_ms = 300_000
                    elapsed_ms = 0
                    while elapsed_ms < deadline_ms:
                        cookies = await context.cookies()
                        if "/login" not in page.url and any(
                            cookie.get("name") == "fc2cmadb-session" for cookie in cookies
                        ):
                            return cookies
                        if page.is_closed():
                            break
                        await page.wait_for_timeout(1_000)
                        elapsed_ms += 1_000
                    raise FC2CMADBAuthError("登录未完成；如出现验证码，请在浏览器中完成后重试")
                finally:
                    await browser.close()
        except FC2CMADBAuthError:
            raise
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                raise PlaywrightUnavailableError("自动登录功能需要安装浏览器组件") from exc
            raise FC2CMADBAuthError(f"FC2CMADB 自动登录失败：{exc}") from exc
