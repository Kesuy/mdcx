from __future__ import annotations

import threading
import traceback
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mdcx.base.web import check_theporndb_api_token
from mdcx.config.enums import Website
from mdcx.config.manager import manager
from mdcx.core.network_check import NetworkCheckSpec, _status_icon, run_network_check, run_network_check_item
from mdcx.crawlers.fc2ppvdb import FC2CMADB_AUTH_PROBE_NUMBER, cookie_str_to_dict
from mdcx.signals import signal_qt


@dataclass(frozen=True)
class CookieCheckResult:
    tips: str


class NetworkController:
    """Own network diagnostics and website Cookie validation for the main window."""

    def __init__(self, window: Any) -> None:
        self.window = window
        self.cancel_event: threading.Event | None = None
        self.future: Any = None

    def toggle_network_check(self) -> None:
        button = self.window.Ui.pushButton_check_net
        if button.text() == "开始检测":
            button.setText("停止检测")
            self.cancel_event = threading.Event()
            try:
                self.future = self.window.task_manager.submit(
                    "network-check",
                    run_network_check(progress=signal_qt.show_net_info, cancel_event=self.cancel_event),
                    on_success=lambda _result: self._network_check_done(),
                    on_error=self._network_check_failed,
                )
            except Exception:
                self._network_check_done()
                error = traceback.format_exc()
                signal_qt.show_traceback_log(error)
                signal_qt.show_net_info(error)
            return

        if button.text() == "停止检测":
            self.stop_network_check()
            return

        # Recover from an unexpected translated/custom button label without
        # leaving an active diagnostic task behind.
        self.stop_network_check(show_message=False)

    def stop_network_check(self, *, show_message: bool = True) -> None:
        if self.cancel_event:
            self.cancel_event.set()
        if show_message:
            signal_qt.show_net_info("\n⛔️ 正在停止网络检测...")
        self.window.Ui.pushButton_check_net.setText("开始检测")

    def _network_check_done(self) -> None:
        self.cancel_event = None
        self.future = None
        button = self.window.Ui.pushButton_check_net
        button.setEnabled(True)
        button.setText("开始检测")

    def _network_check_failed(self, error: str) -> None:
        signal_qt.show_net_info(f"\n⛔️ 网络检测出现异常：{error}")
        signal_qt.show_traceback_log(error)
        self._network_check_done()

    def check_theporndb_token(self) -> None:
        ui = self.window.Ui
        token = ui.lineEdit_api_token_theporndb.text().strip()
        if not token:
            ui.label_theporndb_api_result.setText("❌ 未填写 API Token")
            return
        ui.pushButton_check_theporndb_api.setEnabled(False)
        ui.label_theporndb_api_result.setText("⏳ 正在检测中...")
        try:
            self.window.task_manager.submit_sync(
                "check-theporndb-token",
                lambda: check_theporndb_api_token(token),
                on_success=self._theporndb_check_done,
                on_error=lambda _error: self._theporndb_check_done("❌ API 测试失败，请检查网络或 Token"),
            )
        except Exception:
            self._theporndb_check_done("❌ API 测试失败，请检查网络或 Token")

    def _theporndb_check_done(self, result: str) -> None:
        self.window.Ui.label_theporndb_api_result.setText(result)
        self.window.Ui.pushButton_check_theporndb_api.setEnabled(True)

    def check_javdb_cookie(self) -> None:
        input_cookie = self.window.Ui.plainTextEdit_cookie_javdb.toPlainText().strip()
        if not input_cookie:
            self.window.set_javdb_status.emit("❌ 未填写 Cookie")
            self.window.show_log_text(" ❌ JavDb 未填写 Cookie，可在「设置」-「网络」添加！")
            return
        self.window.set_javdb_status.emit("⏳ 正在检测中...")
        self._submit_cookie_check(
            name="check-javdb-cookie",
            site="JavDb",
            status_signal=self.window.set_javdb_status,
            coroutine=self._check_javdb_cookie_async(input_cookie),
            on_success=self._apply_javdb_cookie_result,
        )

    async def _check_javdb_cookie_async(self, input_cookie: str) -> CookieCheckResult:
        return await self._check_site_cookie(Website.JAVDB, input_cookie, "/v/D16Q5?locale=zh")

    async def _check_site_cookie(self, site: Website, cookie: str, path: str) -> CookieCheckResult:
        if not cookie:
            return CookieCheckResult("❌ 未填写 Cookie")
        headers = {"cookie": cookie}
        if site == Website.JAVBUS:
            headers["Accept-Language"] = "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6"
        is_fc2cmadb = site == Website.FC2PPVDB
        default_url = "https://fc2cmadb.com" if is_fc2cmadb else f"https://{site.value}.com"
        spec = NetworkCheckSpec(
            name=site.value,
            group="刮削站点",
            url=manager.config.get_site_url(site, default_url).rstrip("/") + path,
            site=site,
            headers={} if is_fc2cmadb else headers,
            cookies=cookie_str_to_dict(cookie) if is_fc2cmadb else {},
            validator="fc2cmadb" if is_fc2cmadb else "",
            enable_cf_bypass=True,
        )
        async with manager.acquire_computed() as computed:
            result = await run_network_check_item(spec, client=computed.async_client)
        return CookieCheckResult(f"{_status_icon(result.status)} {result.message}")

    def _apply_javdb_cookie_result(self, result: CookieCheckResult) -> None:
        self.window.set_javdb_status.emit(result.tips)
        self.window.show_log_text(result.tips.replace("❌", " ❌ JavDb").replace("✅", " ✅ JavDb"))

    def check_fc2ppvdb_cookie(self) -> None:
        input_cookie = self.window.Ui.plainTextEdit_cookie_fc2ppvdb.toPlainText().strip()
        if not input_cookie:
            self.window.set_fc2ppvdb_status.emit("❌ 未填写 Cookie")
            self.window.show_log_text(" ❌ FC2CMADB 未填写 Cookie，可在「设置」-「网络」添加！")
            return
        self.window.set_fc2ppvdb_status.emit("⏳ 正在检测中...")
        self._submit_cookie_check(
            name="check-fc2cmadb-cookie",
            site="FC2CMADB",
            status_signal=self.window.set_fc2ppvdb_status,
            coroutine=self._check_fc2ppvdb_cookie_async(input_cookie),
            on_success=self._apply_fc2ppvdb_cookie_result,
        )

    async def _check_fc2ppvdb_cookie_async(self, input_cookie: str) -> CookieCheckResult:
        return await self._check_site_cookie(Website.FC2PPVDB, input_cookie, f"/articles/{FC2CMADB_AUTH_PROBE_NUMBER}")

    def _apply_fc2ppvdb_cookie_result(self, result: CookieCheckResult) -> None:
        self.window.set_fc2ppvdb_status.emit(result.tips)
        self.window.show_log_text(result.tips.replace("❌", " ❌ FC2CMADB").replace("✅", " ✅ FC2CMADB"))

    def check_javbus_cookie(self) -> None:
        input_cookie = self.window.Ui.plainTextEdit_cookie_javbus.toPlainText().strip()
        if not input_cookie:
            self.window.set_javbus_status.emit("❌ 未填写 Cookie")
            return
        self.window.set_javbus_status.emit("⏳ 正在检测中...")
        self._submit_cookie_check(
            name="check-javbus-cookie",
            site="JavBus",
            status_signal=self.window.set_javbus_status,
            coroutine=self._check_javbus_cookie_async(input_cookie),
            on_success=self._apply_javbus_cookie_result,
        )

    async def _check_javbus_cookie_async(self, input_cookie: str) -> CookieCheckResult:
        return await self._check_site_cookie(Website.JAVBUS, input_cookie, "/FSDSS-660")

    def _apply_javbus_cookie_result(self, result: CookieCheckResult) -> None:
        self.window.show_log_text(result.tips.replace("❌", " ❌ JavBus").replace("✅", " ✅ JavBus"))
        self.window.set_javbus_status.emit(result.tips)

    def _submit_cookie_check(
        self,
        *,
        name: str,
        site: str,
        status_signal: Any,
        coroutine: Awaitable[CookieCheckResult],
        on_success: Callable[[CookieCheckResult], None],
    ) -> None:
        try:
            self.window.task_manager.submit(
                name,
                coroutine,
                on_success=on_success,
                on_error=lambda error: self._cookie_check_failed(site, status_signal, error),
            )
        except Exception:
            close = getattr(coroutine, "close", None)
            if close:
                close()
            error = traceback.format_exc()
            self._cookie_check_failed(site, status_signal, error)

    def _cookie_check_failed(self, site: str, status_signal: Any, error: str) -> None:
        tips = f"❌ {site} 检查失败，请查看日志"
        status_signal.emit(tips)
        signal_qt.show_traceback_log(error)
        self.window.show_log_text(f" {tips}")
