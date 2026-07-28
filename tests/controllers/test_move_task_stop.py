import threading
from enum import IntFlag
from pathlib import Path
from types import SimpleNamespace

from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.models.flags import Flags


class _StandardButton(IntFlag):
    Yes = 1
    No = 2


class _MessageBox:
    class Icon:
        Warning = 1

    StandardButton = _StandardButton

    def __init__(self, *_args):
        pass

    def setStandardButtons(self, _buttons):
        pass

    def button(self, _button):
        return SimpleNamespace(setText=lambda _text: None)

    def setDefaultButton(self, _button):
        pass

    def exec(self):
        return self.StandardButton.Yes


def _signal(logs: list[str]):
    return SimpleNamespace(
        stop=False,
        show_log_text=logs.append,
        show_traceback_log=logs.append,
        change_buttons_status=SimpleNamespace(emit=lambda: None),
        reset_buttons_status=SimpleNamespace(emit=lambda: None),
    )


def test_move_stop_finishes_current_file_and_does_not_start_later_files(monkeypatch, tmp_path: Path):
    movie_root = tmp_path / "movies"
    movie_root.mkdir()
    files = [movie_root / f"movie-{index}.mp4" for index in range(3)]
    logs: list[str] = []
    window = MyMAinWindow.__new__(MyMAinWindow)
    window._thread_stop_event = threading.Event()

    def path_settings(_file_path=None, movie_path_override=None):
        if movie_path_override is None:
            return SimpleNamespace(movie_paths=[movie_root])
        return SimpleNamespace(ignore_dirs=[])

    def run_coroutine(coro):
        coro.close()
        return files

    moved: list[Path] = []

    def move_file(source: Path, _destination: Path):
        moved.append(source)
        window._thread_stop_event.set()

    monkeypatch.setattr(main_window_module, "signal_qt", _signal(logs))
    monkeypatch.setattr(main_window_module, "get_movie_path_setting", path_settings)
    monkeypatch.setattr(main_window_module, "executor", SimpleNamespace(run=run_coroutine))
    monkeypatch.setattr(main_window_module.shutil, "move", move_file)
    monkeypatch.setattr(main_window_module.manager.config, "media_type", [".mp4"])
    monkeypatch.setattr(main_window_module.manager.config, "sub_type", [])
    monkeypatch.setattr(Flags, "stop_requested", False)

    window._move_file_thread()

    assert moved == [files[0]]
    assert any("当前文件操作已安全完成" in log for log in logs)


def test_move_start_is_rejected_while_previous_thread_is_alive(monkeypatch):
    logs: list[str] = []
    window = MyMAinWindow.__new__(MyMAinWindow)
    window.threads_list = [SimpleNamespace(is_alive=lambda: True)]
    window._thread_stop_event = threading.Event()
    window._thread_stop_event.set()
    window.pushButton_show_log_clicked = lambda: None
    thread_created = False

    def create_thread(*_args, **_kwargs):
        nonlocal thread_created
        thread_created = True
        raise AssertionError("a replacement thread must not be created")

    monkeypatch.setattr(main_window_module, "QMessageBox", _MessageBox)
    monkeypatch.setattr(main_window_module, "signal_qt", _signal(logs))
    monkeypatch.setattr(main_window_module.threading, "Thread", create_thread)

    window.pushButton_move_mp4_clicked()

    assert thread_created is False
    assert window._thread_stop_event.is_set()
    assert any("未启动新的移动任务" in log for log in logs)


def test_next_move_start_clears_stop_event_after_previous_thread_exits(monkeypatch):
    logs: list[str] = []
    window = MyMAinWindow.__new__(MyMAinWindow)
    window.threads_list = [SimpleNamespace(is_alive=lambda: False)]
    window._thread_stop_event = threading.Event()
    window._thread_stop_event.set()
    window.pushButton_show_log_clicked = lambda: None
    created_threads = []

    class StartedThread:
        def __init__(self, *, target):
            self.target = target
            self.started = False

        def start(self):
            self.started = True

        def is_alive(self):
            return self.started

    def create_thread(*, target):
        thread = StartedThread(target=target)
        created_threads.append(thread)
        return thread

    monkeypatch.setattr(main_window_module, "QMessageBox", _MessageBox)
    monkeypatch.setattr(main_window_module, "signal_qt", _signal(logs))
    monkeypatch.setattr(main_window_module.threading, "Thread", create_thread)

    window.pushButton_move_mp4_clicked()

    assert not window._thread_stop_event.is_set()
    assert len(created_threads) == 1
    assert created_threads[0].started is True
    assert window.threads_list == created_threads
