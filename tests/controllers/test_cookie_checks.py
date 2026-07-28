from types import SimpleNamespace

from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow


class _Signal:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


def test_startup_does_not_check_website_cookies(monkeypatch):
    monkeypatch.setattr(main_window_module, "check_version", lambda: "")
    monkeypatch.setattr(main_window_module.signal_qt, "show_log_text", lambda _message: None)
    monkeypatch.setattr(main_window_module.manager, "config", SimpleNamespace(use_database=False))

    class _Thread:
        def __init__(self, *, target):
            self.target = target

        def start(self):
            return None

    monkeypatch.setattr(main_window_module.threading, "Thread", _Thread)

    class _Window:
        localversion = "3.2"
        new_version = ""
        main_logs_show = _Signal()

        def pushButton_check_javdb_cookie_clicked(self):
            raise AssertionError("startup must not validate JavDB Cookie")

        def pushButton_check_javbus_cookie_clicked(self):
            raise AssertionError("startup must not validate JavBus Cookie")

    MyMAinWindow._show_version_thread(_Window())


def test_javbus_check_rejects_blank_cookie_without_network_thread(monkeypatch):
    started_threads = []

    class _Thread:
        def __init__(self, *, target, args):
            started_threads.append((target, args))

        def start(self):
            raise AssertionError("blank Cookie must not start a network request")

    monkeypatch.setattr(main_window_module.threading, "Thread", _Thread)

    class _Window:
        Ui = SimpleNamespace(plainTextEdit_cookie_javbus=SimpleNamespace(toPlainText=lambda: "   "))
        set_javbus_status = _Signal()

        def _check_javbus_cookie(self, _cookie):
            raise AssertionError("blank Cookie must not be checked")

    window = _Window()
    MyMAinWindow.pushButton_check_javbus_cookie_clicked(window)

    assert started_threads == []
    assert window.set_javbus_status.values == ["❌ 未填写 Cookie"]
