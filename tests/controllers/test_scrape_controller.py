from types import SimpleNamespace

from mdcx.controllers.main_window import scrape_controller
from mdcx.controllers.main_window.scrape_controller import ScrapeController
from mdcx.models.enums import FileMode


class _Button:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text


def _controller(button_text: str) -> ScrapeController:
    window = SimpleNamespace(Ui=SimpleNamespace(pushButton_start_cap=_Button(button_text)))
    return ScrapeController(window)


def test_toggle_starts_default_scrape_only_when_no_resume_list(monkeypatch):
    started = []
    monkeypatch.setattr(scrape_controller, "get_remain_list", lambda: [])
    monkeypatch.setattr(scrape_controller, "start_new_scrape", started.append)

    _controller("开始").toggle()

    assert started == [FileMode.Default]


def test_toggle_preserves_resume_list_and_delegates_stop(monkeypatch):
    started = []
    monkeypatch.setattr(scrape_controller, "get_remain_list", lambda: ["movie.mp4"])
    monkeypatch.setattr(scrape_controller, "start_new_scrape", started.append)

    controller = _controller("开始")
    controller.toggle()
    assert started == []

    stop_calls = []
    controller = _controller("■ 停止")
    monkeypatch.setattr(controller, "stop", lambda: stop_calls.append(True))
    controller.toggle()
    assert stop_calls == [True]


def test_stop_remains_responsive_and_completes_on_qt_thread(monkeypatch):
    import asyncio
    import threading
    import time

    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from mdcx.task_manager import QtTaskManager

    app = QApplication.instance() or QApplication([])
    tasks = QtTaskManager()
    entered = threading.Event()
    release = threading.Event()
    callbacks = []
    ticks = []
    qt_thread = threading.get_ident()

    async def slow_stop():
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)

    monkeypatch.setattr(scrape_controller, "stop_active_scrape", slow_stop)
    monkeypatch.setattr(scrape_controller.manager.config, "switch_on", [])
    monkeypatch.setattr(scrape_controller, "signal_qt", SimpleNamespace(stop=False, show_scrape_info=lambda _: None))
    window = SimpleNamespace(
        Ui=SimpleNamespace(pushButton_start_cap=_Button("■ 停止"), pushButton_start_cap2=_Button("■ 停止")),
        task_manager=tasks,
        _thread_stop_event=threading.Event(),
    )
    controller = ScrapeController(window)
    monkeypatch.setattr(controller, "show_stop_info", lambda: callbacks.append(threading.get_ident()))
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start(1)
    try:
        controller.stop()
        deadline = time.monotonic() + 2
        while (not entered.is_set() or not ticks) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.001)
        assert entered.is_set()
        assert ticks
        assert not callbacks
        assert window.Ui.pushButton_start_cap.text() == " ■ 停止中 "
        release.set()
        while not callbacks and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.001)
        assert callbacks == [qt_thread]
    finally:
        release.set()
        timer.stop()
        tasks.shutdown()
