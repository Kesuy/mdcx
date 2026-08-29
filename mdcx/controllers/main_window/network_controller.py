from __future__ import annotations

import re
import threading
import traceback
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mdcx.config.enums import Website
from mdcx.config.manager import manager
from mdcx.core.network_check import run_network_check
from mdcx.crawlers.fc2ppvdb import validate_fc2cmadb_cookie
from mdcx.signals import signal_qt


@dataclass(frozen=True)
class CookieCheckResult:
    tips: str
    clear_cookie: bool = False
    save_config: bool = False


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
        tips = "❌ 未填写 Cookie，影响 FC2 刮削！"
        if not input_cookie:
            return CookieCheckResult(tips)
        tips = "✅ 连接正常！"
        header = {"cookie": input_cookie}
        javdb_url = manager.config.get_site_url(Website.JAVDB, "https://javdb.com") + "/v/D16Q5?locale=zh"
        try:
            async with manager.acquire_computed() as computed:
                response, error = await computed.async_client.get_text(javdb_url, headers=header)
            if response is None:
                if error and "Cookie" in error:
                    if manager.config.javdb != input_cookie:
                        tips = "❌ Cookie 已过期！"
                    else:
                        tips = "❌ Cookie 已过期！已清理！(不清理无法访问)"
                        return CookieCheckResult(tips, clear_cookie=True, save_config=True)
                else:
                    tips = f"❌ 连接失败！请检查网络或代理设置！ {error or '未知错误'}"
            elif "The owner of this website has banned your access based on your browser's behaving" in response:
                ip_address = re.findall(r"(\d+\.\d+\.\d+\.\d+)", response)
                ip_text = ip_address[0] + " " if ip_address else ""
                tips = f"❌ 你的 IP {ip_text}被 JavDb 封了！"
            elif "Due to copyright restrictions" in response or "Access denied" in response:
                tips = "❌ 当前 IP 被禁止访问！请使用非日本节点！"
            elif "ray-id" in response:
                tips = "❌ 访问被 CloudFlare 拦截！"
            elif "/logout" in response:
                vip_info = "未开通 VIP"
                if "icon-diamond" in response or "/v/D16Q5" in response:
                    vip_info = "已开通 VIP"
                if manager.config.javdb != input_cookie:
                    tips = f"✅ 连接正常！（{vip_info}）Cookie 已保存！"
                    return CookieCheckResult(tips, save_config=True)
                tips = f"✅ 连接正常！（{vip_info}）"
            elif manager.config.javdb != input_cookie:
                tips = "❌ Cookie 无效！请重新填写！"
            else:
                tips = "❌ Cookie 无效！已清理！"
                return CookieCheckResult(tips, clear_cookie=True, save_config=True)
        except Exception as exc:
            tips = f"❌ 连接失败！请检查网络或代理设置！ {exc}"
            signal_qt.show_traceback_log(tips)
        return CookieCheckResult(tips)

    def _apply_javdb_cookie_result(self, result: CookieCheckResult) -> None:
        if result.clear_cookie:
            self.window.set_javdb_cookie.emit("")
        if result.save_config:
            self.window.exec_save_config.emit()
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
        if not input_cookie:
            return CookieCheckResult("❌ 未填写 Cookie")

        async with manager.acquire_computed() as computed:
            valid, error = await validate_fc2cmadb_cookie(
                computed.async_client,
                input_cookie,
                use_proxy=manager.config.use_proxy,
            )
        if not valid:
            return CookieCheckResult(f"❌ Cookie 检查失败：{error}")
        if manager.config.fc2ppvdb != input_cookie:
            return CookieCheckResult("✅ 登录状态有效，Cookie 已保存！", save_config=True)
        return CookieCheckResult("✅ 登录状态有效！")

    def _apply_fc2ppvdb_cookie_result(self, result: CookieCheckResult) -> None:
        if result.save_config:
            self.window.exec_save_config.emit()
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
        tips = "✅ 连接正常！"
        headers = {
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
            "cookie": input_cookie,
        }
        javbus_url = manager.config.get_site_url(Website.JAVBUS, "https://javbus.com") + "/FSDSS-660"
        try:
            async with manager.acquire_computed() as computed:
                response, error = await computed.async_client.get_text(javbus_url, headers=headers)
            if response is None:
                tips = f"❌ 连接失败！请检查网络或代理设置！ {error}"
            elif "lostpasswd" in response:
                tips = (
                    "❌ Cookie 无效！"
                    if input_cookie
                    else "❌ 当前节点需要 Cookie 才能刮削！请填写 Cookie 或更换节点！"
                )
            elif manager.config.javbus != input_cookie:
                return CookieCheckResult("✅ 连接正常！Cookie 已保存！  ", save_config=True)
        except Exception as exc:
            tips = f"❌ 连接失败！请检查网络或代理设置！ {exc}"
        return CookieCheckResult(tips)

    def _apply_javbus_cookie_result(self, result: CookieCheckResult) -> None:
        if result.save_config:
            self.window.exec_save_config.emit()
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
