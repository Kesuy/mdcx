from types import SimpleNamespace

from mdcx.controllers.main_window import scrape_controller
from mdcx.controllers.main_window.scrape_controller import ScrapeController
from mdcx.models.enums import FileMode


class _Button:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


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
