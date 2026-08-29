import threading
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication, QTextBrowser

from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.network_controller import NetworkController
from mdcx.controllers.main_window.usage_guide import build_usage_guide, setup_usage_guide

APP = QApplication.instance() or QApplication([])


def test_usage_guide_covers_current_workflows_and_replaces_legacy_copy():
    guide = build_usage_guide()

    assert "MDCx 使用说明" in guide
    assert "MDCx 3.8.4 使用说明" not in guide
    assert "正常模式" in guide
    assert "读取模式" in guide
    assert "JSON 配置" in guide
    assert "CF Bypass" in guide
    assert "FC2CMADB" in guide
    assert "保持原始比例缩放" in guide
    assert "AVDC-GUI" not in guide
    assert "proxy=127.0.0.1:1080" not in guide


def test_setup_usage_guide_uses_log_like_plain_text_content():
    browser = QTextBrowser()
    window = SimpleNamespace(Ui=SimpleNamespace(textBrowser_about=browser))

    setup_usage_guide(window)

    assert browser.toPlainText().startswith("📘 MDCx 使用说明")
    assert "🔄 更新与反馈" in browser.toPlainText()
    assert browser.textCursor().position() == 0


def test_network_check_button_keeps_shared_rounded_style():
    button = main_window_module.QPushButton()
    button.setObjectName("pushButton_check_net")
    button.setText("开始检测")
    started: list[bool] = []

    class FakeTaskManager:
        def submit(self, name, coroutine, **_kwargs):
            started.append(name)
            coroutine.close()
            return object()

    window = SimpleNamespace(
        Ui=SimpleNamespace(pushButton_check_net=button),
        task_manager=FakeTaskManager(),
    )
    window.network_controller = NetworkController(window)

    MyMAinWindow.pushButton_check_net_clicked(window)

    assert started == ["network-check"]
    assert button.text() == "停止检测"
    assert button.styleSheet() == ""

    cancel_event = threading.Event()
    window.network_controller.cancel_event = cancel_event
    MyMAinWindow.pushButton_check_net_clicked(window)

    assert cancel_event.is_set()
    assert button.text() == "开始检测"
    assert button.styleSheet() == ""
