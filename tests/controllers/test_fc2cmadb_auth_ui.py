from PyQt6.QtWidgets import QApplication, QLineEdit, QMainWindow

from mdcx.controllers.main_window import load_config as load_config_module
from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.views.MDCx import Ui_MDCx

APP = QApplication.instance() or QApplication([])


def _setup_fc2cmadb_ui():
    window = QMainWindow()
    window.Ui = Ui_MDCx()
    window.Ui.setupUi(window)
    MyMAinWindow._setup_fc2ppvdb_cookie_ui(window)
    return window


def test_fc2cmadb_auth_ui_defaults_to_manual_and_masks_password():
    window = _setup_fc2cmadb_ui()

    assert window.Ui.radioButton_fc2cmadb_manual.isChecked() is True
    assert window.Ui.radioButton_fc2cmadb_auto.isChecked() is False
    assert window.Ui.lineEdit_fc2cmadb_password.echoMode() == QLineEdit.EchoMode.Password
    assert window.Ui.lineEdit_fc2cmadb_username.isHidden() is True
    assert window.Ui.lineEdit_fc2cmadb_password.isHidden() is True
    assert window.Ui.pushButton_fc2cmadb_login.isHidden() is True


def test_fc2cmadb_auto_mode_shows_runtime_login_fields():
    window = _setup_fc2cmadb_ui()

    window.Ui.radioButton_fc2cmadb_auto.setChecked(True)

    assert window.Ui.lineEdit_fc2cmadb_username.isHidden() is False
    assert window.Ui.lineEdit_fc2cmadb_password.isHidden() is False
    assert window.Ui.pushButton_fc2cmadb_login.isHidden() is False


def test_fc2cmadb_auto_login_explains_installed_browser_selection():
    window = _setup_fc2cmadb_ui()

    tooltip = window.Ui.pushButton_fc2cmadb_login.toolTip()

    assert "Microsoft Edge" in tooltip
    assert "Google Chrome" in tooltip
    assert "复用专用浏览器资料" in tooltip


def test_fc2cmadb_login_click_keeps_password_for_the_app_session(monkeypatch):
    runtime_credentials = []
    started_threads = []

    class FakeLineEdit:
        def __init__(self, value):
            self.value = value

        def text(self):
            return self.value

        def clear(self):
            self.value = ""

    class FakeSignal:
        def emit(self, _value):
            pass

    class FakeThread:
        def __init__(self, *, target, args, daemon):
            started_threads.append((target, args, daemon))

        def start(self):
            pass

    class FakeWindow:
        Ui = type(
            "FakeUi",
            (),
            {
                "lineEdit_fc2cmadb_username": FakeLineEdit("test-user"),
                "lineEdit_fc2cmadb_password": FakeLineEdit("runtime-password"),
            },
        )()
        set_fc2ppvdb_status = FakeSignal()

        @staticmethod
        def _login_fc2cmadb(_username, _password):
            pass

    monkeypatch.setattr(main_window_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(
        main_window_module,
        "set_fc2cmadb_runtime_credentials",
        lambda username, password: runtime_credentials.append((username, password)),
    )

    MyMAinWindow.pushButton_fc2cmadb_login_clicked(FakeWindow())

    assert FakeWindow.Ui.lineEdit_fc2cmadb_password.text() == "runtime-password"
    assert runtime_credentials == [("test-user", "runtime-password")]
    assert len(started_threads) == 1


def test_fc2cmadb_config_reload_keeps_runtime_password_in_the_widget():
    window = _setup_fc2cmadb_ui()
    window.Ui.lineEdit_fc2cmadb_password.setText("runtime-password")
    window._update_fc2cmadb_auth_mode_ui = lambda: None
    manager = type(
        "FakeConfigManager",
        (),
        {
            "config": type(
                "FakeConfig",
                (),
                {
                    "fc2ppvdb": "fc2cmadb-session=test-cookie",
                    "fc2cmadb_auth_mode": "auto",
                },
            )()
        },
    )()

    load_config_module._load_fc2cmadb_auth_config(window, manager)

    assert window.Ui.lineEdit_fc2cmadb_password.text() == "runtime-password"
    assert window.Ui.radioButton_fc2cmadb_auto.isChecked() is True
    assert window.Ui.plainTextEdit_cookie_fc2ppvdb.toPlainText() == "fc2cmadb-session=test-cookie"


def test_cookie_settings_visually_separate_each_website():
    window = _setup_fc2cmadb_ui()

    section_titles = [
        window.Ui.label_javdb_cookie_section,
        window.Ui.label_javbus_cookie_section,
        window.Ui.label_fc2cmadb_cookie_section,
    ]

    assert [label.text() for label in section_titles] == ["JavDB", "JavBus", "FC2CMADB"]
    assert all(label.styleSheet() for label in section_titles)
    assert [
        window.Ui.gridLayout_10.getItemPosition(window.Ui.gridLayout_10.indexOf(label))[0] for label in section_titles
    ] == [
        0,
        4,
        8,
    ]


def test_fc2cmadb_login_worker_updates_cookie_without_exposing_password(monkeypatch):
    emitted_cookies = []
    emitted_status = []
    logs = []
    runtime_credentials = []

    class FakeSignal:
        def __init__(self, values):
            self.values = values

        def emit(self, value):
            self.values.append(value)

    class FakeAuthManager:
        async def login(self, username, password):
            assert username == "test-user"
            assert password == "runtime-password"
            return "fc2cmadb-session=new-session"

    class FakeWindow:
        set_fc2ppvdb_cookie = FakeSignal(emitted_cookies)
        set_fc2ppvdb_status = FakeSignal(emitted_status)

        @staticmethod
        def show_log_text(message):
            logs.append(message)

    monkeypatch.setattr(main_window_module, "FC2CMADBAuthManager", FakeAuthManager)
    monkeypatch.setattr(
        main_window_module,
        "set_fc2cmadb_runtime_credentials",
        lambda username, password: runtime_credentials.append((username, password)),
    )

    MyMAinWindow._login_fc2cmadb(FakeWindow(), "test-user", "runtime-password")

    assert emitted_cookies == ["fc2cmadb-session=new-session"]
    assert emitted_status == ["✅ 自动登录成功，Cookie 已保存！"]
    assert runtime_credentials == [("test-user", "runtime-password")]
    assert all("runtime-password" not in message for message in logs)
