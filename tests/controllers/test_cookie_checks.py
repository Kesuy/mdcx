from types import SimpleNamespace

import pytest

from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window import network_controller as network_controller_module
from mdcx.controllers.main_window import window_lifecycle as window_lifecycle_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.network_controller import CookieCheckResult, NetworkController


class _Signal:
    def __init__(self):
        self.values = []

    def emit(self, value=None):
        self.values.append(value)


def _api_window(token, task_manager):
    statuses, enabled = [], []
    window = SimpleNamespace(
        Ui=SimpleNamespace(
            lineEdit_api_token_theporndb=SimpleNamespace(text=lambda: token),
            label_theporndb_api_result=SimpleNamespace(setText=statuses.append),
            pushButton_check_theporndb_api=SimpleNamespace(setEnabled=enabled.append),
        ),
        task_manager=task_manager,
    )
    return window, statuses, enabled


def test_api_check_uses_current_input_and_displays_result(monkeypatch):
    tasks = []
    tokens = []
    monkeypatch.setattr(
        network_controller_module, "check_theporndb_api_token", lambda token: tokens.append(token) or "✅ 连接正常！"
    )
    window, statuses, enabled = _api_window(
        " new-token ",
        SimpleNamespace(submit_sync=lambda name, function, **callbacks: tasks.append((name, function, callbacks))),
    )
    NetworkController(window).check_theporndb_token()

    assert statuses == ["⏳ 正在检测中..."]
    assert enabled == [False]
    name, function, callbacks = tasks[0]
    assert name == "check-theporndb-token"
    callbacks["on_success"](function())
    assert tokens == ["new-token"]
    assert statuses[-1] == "✅ 连接正常！"
    assert enabled == [False, True]


def test_api_check_rejects_blank_input_without_submitting():
    window, statuses, enabled = _api_window("   ", None)
    NetworkController(window).check_theporndb_token()
    assert statuses == ["❌ 未填写 API Token"]
    assert enabled == []


@pytest.mark.parametrize("submission_failure", [True, False])
def test_api_check_failure_restores_button(submission_failure):
    def submit(_name, _function, **callbacks):
        if submission_failure:
            raise RuntimeError("executor unavailable")
        callbacks["on_error"]("request failed")

    window, statuses, enabled = _api_window("token", SimpleNamespace(submit_sync=submit))
    NetworkController(window).check_theporndb_token()
    assert statuses[-1].startswith("❌ API 测试失败")
    assert enabled == [False, True]


def test_startup_does_not_check_website_cookies_or_api_tokens(monkeypatch):
    monkeypatch.setattr(main_window_module, "check_version", lambda: "")
    monkeypatch.setattr(window_lifecycle_module.signal_qt, "show_log_text", lambda _message: None)
    monkeypatch.setattr(window_lifecycle_module.manager, "config", SimpleNamespace(use_database=False))

    submitted = []

    class _TaskManager:
        def submit_sync(self, name, _function, **_kwargs):
            submitted.append(name)

    class _Window:
        localversion = "3.2"
        new_version = ""
        main_logs_show = _Signal()
        task_manager = _TaskManager()

        def pushButton_check_javdb_cookie_clicked(self):
            raise AssertionError("startup must not validate JavDB Cookie")

        def pushButton_check_javbus_cookie_clicked(self):
            raise AssertionError("startup must not validate JavBus Cookie")

    MyMAinWindow._show_version_thread(_Window())
    assert submitted == []


def test_javbus_check_rejects_blank_cookie_without_network_task():
    class _Window:
        Ui = SimpleNamespace(plainTextEdit_cookie_javbus=SimpleNamespace(toPlainText=lambda: "   "))
        set_javbus_status = _Signal()

    window = _Window()
    window.network_controller = NetworkController(window)
    MyMAinWindow.pushButton_check_javbus_cookie_clicked(window)

    assert window.set_javbus_status.values == ["❌ 未填写 Cookie"]


def test_javdb_result_preserves_cookie_and_does_not_save_config():
    logs = []
    window = SimpleNamespace(
        set_javdb_cookie=_Signal(),
        set_javdb_status=_Signal(),
        exec_save_config=_Signal(),
        show_log_text=logs.append,
    )
    controller = NetworkController(window)

    controller._apply_javdb_cookie_result(CookieCheckResult("⚠️ 站点可访问，但 JavDB Cookie 可能无效"))

    assert window.set_javdb_cookie.values == []
    assert window.exec_save_config.values == []
    assert window.set_javdb_status.values == ["⚠️ 站点可访问，但 JavDB Cookie 可能无效"]
    assert logs == ["⚠️ 站点可访问，但 JavDB Cookie 可能无效"]


def test_cookie_task_submission_failure_restores_visible_status():
    class _FailingTaskManager:
        def submit(self, *_args, **_kwargs):
            raise RuntimeError("background executor unavailable")

    logs = []
    window = SimpleNamespace(
        Ui=SimpleNamespace(plainTextEdit_cookie_javbus=SimpleNamespace(toPlainText=lambda: "cookie=value")),
        set_javbus_status=_Signal(),
        task_manager=_FailingTaskManager(),
        show_log_text=logs.append,
    )

    NetworkController(window).check_javbus_cookie()

    assert window.set_javbus_status.values == ["⏳ 正在检测中...", "❌ JavBus 检查失败，请查看日志"]
    assert logs == [" ❌ JavBus 检查失败，请查看日志"]


@pytest.mark.asyncio
@pytest.mark.parametrize("site", ["javdb", "javbus", "fc2ppvdb"])
async def test_cookie_checks_use_shared_diagnostics_with_current_input(monkeypatch, site):
    from contextlib import asynccontextmanager

    from mdcx.core.network_check import NetworkCheckResult, NetworkCheckStatus

    client = object()

    @asynccontextmanager
    async def acquire():
        yield SimpleNamespace(async_client=client)

    monkeypatch.setattr(network_controller_module.manager, "acquire_computed", acquire)
    calls = []

    async def check(spec, **kwargs):
        calls.append(spec)
        assert kwargs["client"] is client
        return NetworkCheckResult(spec, NetworkCheckStatus.WARNING, "被 Cloudflare 挑战页拦截")

    monkeypatch.setattr(network_controller_module, "run_network_check_item", check)
    controller = NetworkController(SimpleNamespace())
    result = await getattr(controller, f"_check_{site}_cookie_async")("session=synthetic")
    assert result.tips == "⚠️ 被 Cloudflare 挑战页拦截"
    assert (
        calls[0].cookies == {"session": "synthetic"}
        if site == "fc2ppvdb"
        else calls[0].headers["cookie"] == "session=synthetic"
    )
