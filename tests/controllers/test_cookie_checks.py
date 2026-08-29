from types import SimpleNamespace

from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.network_controller import CookieCheckResult, NetworkController


class _Signal:
    def __init__(self):
        self.values = []

    def emit(self, value=None):
        self.values.append(value)


def test_startup_does_not_check_website_cookies(monkeypatch):
    monkeypatch.setattr(main_window_module, "check_version", lambda: "")
    monkeypatch.setattr(main_window_module.signal_qt, "show_log_text", lambda _message: None)
    monkeypatch.setattr(main_window_module.manager, "config", SimpleNamespace(use_database=False))

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
    assert submitted == ["check-theporndb-token"]


def test_javbus_check_rejects_blank_cookie_without_network_task():
    class _Window:
        Ui = SimpleNamespace(plainTextEdit_cookie_javbus=SimpleNamespace(toPlainText=lambda: "   "))
        set_javbus_status = _Signal()

    window = _Window()
    window.network_controller = NetworkController(window)
    MyMAinWindow.pushButton_check_javbus_cookie_clicked(window)

    assert window.set_javbus_status.values == ["❌ 未填写 Cookie"]


def test_javdb_result_clears_expired_cookie_and_persists_config():
    logs = []
    window = SimpleNamespace(
        set_javdb_cookie=_Signal(),
        set_javdb_status=_Signal(),
        exec_save_config=_Signal(),
        show_log_text=logs.append,
    )
    controller = NetworkController(window)

    controller._apply_javdb_cookie_result(
        CookieCheckResult("❌ Cookie 已过期！已清理！", clear_cookie=True, save_config=True)
    )

    assert window.set_javdb_cookie.values == [""]
    assert window.exec_save_config.values == [None]
    assert window.set_javdb_status.values == ["❌ Cookie 已过期！已清理！"]
    assert logs == [" ❌ JavDb Cookie 已过期！已清理！"]


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
