from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

from ..config.manager import manager
from ..crawlers.fc2ppvdb import cookie_dict_to_str, validate_fc2cmadb_cookie

BrowserLogin = Callable[[str, str], Awaitable[list[dict[str, Any]]]]
CookieValidator = Callable[[str], Awaitable[tuple[bool, str]]]


class FC2CMADBAuthError(RuntimeError):
    """Raised when FC2CMADB browser authentication cannot produce a valid Cookie."""


class PlaywrightUnavailableError(FC2CMADBAuthError):
    """Raised when optional Playwright browser components are unavailable."""


def _build_playwright_proxy(proxy_server: str | None) -> dict[str, str] | None:
    if not proxy_server:
        return None

    try:
        parsed = urlsplit(proxy_server)
        scheme = parsed.scheme.lower()
        if scheme and scheme not in {"http", "https", "socks4", "socks5", "socks5h"}:
            raise ValueError
        if parsed.username is None and parsed.password is None:
            return {"server": proxy_server}
        if not parsed.scheme or not parsed.hostname or parsed.path not in {"", "/"}:
            raise ValueError
        if scheme.startswith("socks"):
            raise FC2CMADBAuthError(
                "系统浏览器不支持需要用户名或密码的 SOCKS 代理，请改用 HTTP/HTTPS 认证代理"
            ) from None

        host = parsed.hostname
        if ":" in host:
            host = f"[{host}]"
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"

        proxy = {"server": urlunsplit((scheme, host, "", "", ""))}
        if parsed.username is not None:
            proxy["username"] = unquote(parsed.username)
        if parsed.password is not None:
            proxy["password"] = unquote(parsed.password)
        return proxy
    except (TypeError, ValueError) as exc:
        raise FC2CMADBAuthError("MDCx 代理配置无效，无法启动自动登录浏览器") from exc


class FC2CMADBAuthManager:
    def __init__(
        self,
        *,
        config_manager=manager,
        browser_login: BrowserLogin | None = None,
        cookie_validator: CookieValidator | None = None,
    ) -> None:
        self._config_manager = config_manager
        self._browser_login = browser_login or self._login_with_configured_browser
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
    async def _launch_installed_browser(chromium, proxy_server: str | None = None):
        playwright_proxy = _build_playwright_proxy(proxy_server)
        for channel in ("msedge", "chrome"):
            try:
                launch_options = {"channel": channel, "headless": False}
                if playwright_proxy is not None:
                    launch_options["proxy"] = playwright_proxy
                return await chromium.launch(**launch_options)
            except Exception as exc:
                if "is not found" not in str(exc):
                    raise
        raise PlaywrightUnavailableError("未检测到 Microsoft Edge 或 Google Chrome，请先安装其中一个浏览器")

    @staticmethod
    async def _launch_persistent_browser_context(
        chromium,
        user_data_dir: Path,
        proxy_server: str | None = None,
    ):
        playwright_proxy = _build_playwright_proxy(proxy_server)
        for channel in ("msedge", "chrome"):
            try:
                launch_options = {
                    "channel": channel,
                    "headless": False,
                    "no_viewport": True,
                    "ignore_default_args": ["--enable-automation"],
                }
                if playwright_proxy is not None:
                    launch_options["proxy"] = playwright_proxy
                return await chromium.launch_persistent_context(
                    str(user_data_dir),
                    **launch_options,
                )
            except Exception as exc:
                if "is not found" not in str(exc):
                    raise
        raise PlaywrightUnavailableError("未检测到 Microsoft Edge 或 Google Chrome，请先安装其中一个浏览器")

    async def _login_with_configured_browser(self, username: str, password: str) -> list[dict[str, Any]]:
        config = self._config_manager.config
        proxy_server = config.proxy if config.use_proxy else None
        user_data_dir = self._config_manager.data_folder / ".fc2cmadb-browser"
        return await type(self)._login_with_playwright(
            username,
            password,
            proxy_server,
            user_data_dir,
        )

    @staticmethod
    async def _complete_browser_login(
        page,
        context,
        username: str,
        password: str,
        *,
        timeout_ms: int = 300_000,
    ) -> list[dict[str, Any]]:
        username_input = page.locator('input[name="email"], input[name="username"], input[type="email"]').first
        password_input = page.locator('input[name="password"], input[type="password"]').first
        submit_button = page.locator('button[type="submit"], input[type="submit"]').first
        turnstile_response = page.locator(
            'input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]'
        ).first
        credentials_filled = False
        submit_attempted = False
        elapsed_ms = 0

        while elapsed_ms < timeout_ms:
            if page.is_closed():
                break

            cookies = await context.cookies()
            if "/login" not in page.url and any(
                cookie.get("name") == "fc2cmadb-session" and cookie.get("value") for cookie in cookies
            ):
                return cookies

            fields_ready = all([await locator.count() for locator in (username_input, password_input, submit_button)])
            if fields_ready:
                try:
                    credentials_filled = (
                        await username_input.input_value() == username
                        and await password_input.input_value() == password
                    )
                    if not credentials_filled:
                        await username_input.fill(username)
                        await password_input.fill(password)
                        credentials_filled = (
                            await username_input.input_value() == username
                            and await password_input.input_value() == password
                        )
                except Exception:
                    # Cloudflare may replace the login DOM while it verifies the browser.
                    # Mark the old fill stale so the next stable form is populated again.
                    credentials_filled = False
            else:
                credentials_filled = False

            if credentials_filled and not submit_attempted:
                try:
                    has_turnstile = bool(await turnstile_response.count())
                    turnstile_ready = not has_turnstile or bool(await turnstile_response.input_value())
                    if turnstile_ready and await submit_button.is_enabled():
                        await submit_button.click()
                        submit_attempted = True
                except Exception:
                    # A challenge can replace the form between readiness checks and click.
                    # Leave the browser open and retry only after the form becomes stable.
                    pass

            await page.wait_for_timeout(1_000)
            elapsed_ms += 1_000

        raise FC2CMADBAuthError("登录未完成；如出现验证码，请在浏览器中完成后重试")

    @staticmethod
    async def _login_with_playwright(
        username: str,
        password: str,
        proxy_server: str | None = None,
        user_data_dir: Path | None = None,
    ) -> list[dict[str, Any]]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PlaywrightUnavailableError("自动登录组件缺失，请重新安装 MDCx") from exc

        try:
            async with async_playwright() as playwright:
                profile_dir = user_data_dir or manager.data_folder / ".fc2cmadb-browser"
                context = await FC2CMADBAuthManager._launch_persistent_browser_context(
                    playwright.chromium,
                    profile_dir,
                    proxy_server,
                )
                try:
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto("https://fc2cmadb.com/login", wait_until="domcontentloaded")
                    return await FC2CMADBAuthManager._complete_browser_login(
                        page,
                        context,
                        username,
                        password,
                    )
                finally:
                    await context.close()
        except FC2CMADBAuthError:
            raise
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                raise PlaywrightUnavailableError("自动登录组件缺失，请重新安装 MDCx") from None
            raise FC2CMADBAuthError("FC2CMADB 自动登录失败，请检查浏览器、网络或代理设置") from None
