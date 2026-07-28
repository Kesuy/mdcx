"""Task-scoped FC2CMADB authentication recovery primitives."""

import asyncio
import threading
from collections.abc import Callable

from ..config.manager import manager

RuntimeCredentials = tuple[str, str]
CredentialsGetter = Callable[[], RuntimeCredentials | None]
_RUNTIME_CREDENTIALS: RuntimeCredentials | None = None
_RUNTIME_CREDENTIALS_LOCK = threading.Lock()


class FC2CMADBAuthenticationError(RuntimeError):
    """A definitive FC2CMADB authentication failure."""


class FC2CMADBValidationUnavailable(RuntimeError):
    """Cookie validity could not be determined due to a non-authentication failure."""


def set_fc2cmadb_runtime_credentials(username: str, password: str) -> None:
    """Retain credentials in process memory for automatic refreshes in this app session."""
    global _RUNTIME_CREDENTIALS
    with _RUNTIME_CREDENTIALS_LOCK:
        _RUNTIME_CREDENTIALS = (username, password)


def get_fc2cmadb_runtime_credentials() -> RuntimeCredentials | None:
    with _RUNTIME_CREDENTIALS_LOCK:
        return _RUNTIME_CREDENTIALS


def is_fc2cmadb_authentication_failure(error: str) -> bool:
    """Return whether a crawler error definitively means the session is unauthenticated."""
    normalized = error.lower()
    return any(
        marker in normalized
        for marker in (
            "http 401",
            "登录页",
            "登录页面",
            "未登录",
            "unauthenticated",
        )
    )


class FC2CMADBSessionManager:
    """Coordinate validation and at most one browser refresh per crawler task."""

    def __init__(
        self,
        *,
        config_manager=manager,
        auth_manager=None,
        credentials_getter: CredentialsGetter = get_fc2cmadb_runtime_credentials,
    ) -> None:
        if auth_manager is None:
            from .fc2cmadb import FC2CMADBAuthManager

            auth_manager = FC2CMADBAuthManager(config_manager=config_manager)
        self._config_manager = config_manager
        self._auth_manager = auth_manager
        self._credentials_getter = credentials_getter
        self._preflight_lock = asyncio.Lock()
        self._preflight_complete = False
        self._preflight_error: RuntimeError | None = None
        self._refresh_lock = asyncio.Lock()
        self._refresh_attempted = False
        self._refresh_cookie = ""
        self._refresh_error: FC2CMADBAuthenticationError | None = None

    async def ensure_cookie_valid(self) -> None:
        async with self._preflight_lock:
            if self._preflight_complete:
                if self._preflight_error is not None:
                    raise self._preflight_error
                return

            cookie = self._auth_manager.get_cookie()
            valid, error = await self._auth_manager.validate_cookie(cookie)
            try:
                if valid:
                    return
                if "Cookie 无效或已过期" not in error:
                    raise FC2CMADBValidationUnavailable(error or "暂时无法验证 FC2CMADB Cookie")
                await self.recover_after_authentication_failure(cookie)
            except RuntimeError as exc:
                self._preflight_error = exc
                raise
            finally:
                self._preflight_complete = True

    async def recover_after_authentication_failure(self, failed_cookie: str) -> str:
        current_cookie = self._auth_manager.get_cookie()
        if current_cookie != failed_cookie:
            return current_cookie

        async with self._refresh_lock:
            current_cookie = self._auth_manager.get_cookie()
            if current_cookie != failed_cookie:
                return current_cookie
            if self._refresh_attempted:
                if self._refresh_error is not None:
                    raise self._refresh_error
                raise FC2CMADBAuthenticationError(
                    "FC2CMADB Cookie 已经刷新一次，但认证仍然失败；本次任务不会再次自动登录"
                )

            self._refresh_attempted = True
            if self._config_manager.config.fc2cmadb_auth_mode != "auto":
                self._refresh_error = FC2CMADBAuthenticationError("FC2CMADB Cookie 已失效，请在设置中更新手动 Cookie")
                raise self._refresh_error

            credentials = self._credentials_getter()
            if credentials is None:
                self._refresh_error = FC2CMADBAuthenticationError(
                    "FC2CMADB Cookie 已失效，请先在设置中重新执行自动登录"
                )
                raise self._refresh_error

            try:
                self._refresh_cookie = await self._auth_manager.login(*credentials)
            except Exception as exc:
                self._refresh_error = FC2CMADBAuthenticationError(f"FC2CMADB Cookie 自动刷新失败：{exc}")
                raise self._refresh_error from exc
            return self._refresh_cookie
