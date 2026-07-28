from pathlib import Path

import pytest

from mdcx.config.extend import MoviePathSetting
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags


@pytest.mark.asyncio
async def test_run_uses_copied_remain_list(monkeypatch: pytest.MonkeyPatch):
    from mdcx.core import scraper as scraper_module

    Flags.reset()
    movie_list = [Path("MIAA-001.mp4"), Path("MIAA-002.mp4"), Path("MIAA-003.mp4"), Path("MIAA-004.mp4")]
    origin_first = movie_list[0]

    async def fake_run_tasks_with_limit(_self, scheduled_list: list[Path], _task_count: int, _thread_number: int):
        assert scheduled_list is movie_list
        remaining, _, _ = Flags.remain_snapshot()
        assert remaining == scheduled_list

        assert Flags.remove_remain_path(origin_first)

        assert len(scheduled_list) == 4
        assert scheduled_list[0] == origin_first
        Flags.scrape_done = _task_count

    async def fake_save_success_list(_old_path=None, _new_path=None):
        return None

    async def fake_clean_empty_folders(_path: Path, _file_mode: FileMode):
        return None

    def fake_get_movie_path_setting(_file_path=None, movie_path_override=None):
        movie_path = Path(movie_path_override) if movie_path_override is not None else Path(".")
        return MoviePathSetting(
            movie_path=movie_path,
            movie_paths=[movie_path],
            success_folder=movie_path,
            failed_folder=movie_path,
            ignore_dirs=[],
            extrafanart_folder=movie_path,
            softlink_path=movie_path,
        )

    monkeypatch.setattr(scraper_module.Scraper, "_run_tasks_with_limit", fake_run_tasks_with_limit)
    monkeypatch.setattr(scraper_module, "save_success_list", fake_save_success_list)
    monkeypatch.setattr(scraper_module, "_clean_empty_fodlers", fake_clean_empty_folders)
    monkeypatch.setattr(scraper_module, "get_movie_path_setting", fake_get_movie_path_setting)
    monkeypatch.setattr(scraper_module.manager.config, "thread_number", 4)
    monkeypatch.setattr(scraper_module.manager.config, "thread_time", 0)
    monkeypatch.setattr(scraper_module.manager.config, "main_mode", 1)
    monkeypatch.setattr(scraper_module.manager.config, "switch_on", [])
    monkeypatch.setattr(scraper_module.manager.config, "scrape_softlink_path", False)
    monkeypatch.setattr(scraper_module.manager.config, "emby_on", [])
    monkeypatch.setattr(scraper_module.manager.config, "actor_photo_kodi_auto", False)

    scraper = scraper_module.Scraper(crawler_provider=object())
    await scraper._run(FileMode.Default, movie_list)

    assert movie_list == [Path("MIAA-001.mp4"), Path("MIAA-002.mp4"), Path("MIAA-003.mp4"), Path("MIAA-004.mp4")]
    remaining, _, _ = Flags.remain_snapshot()
    assert remaining == [Path("MIAA-002.mp4"), Path("MIAA-003.mp4"), Path("MIAA-004.mp4")]


@pytest.mark.asyncio
async def test_unexpected_cancelled_scrape_task_is_not_silent(monkeypatch: pytest.MonkeyPatch):
    from mdcx.core import scraper as scraper_module

    Flags.reset()
    scraper_module.signal.stop = False
    Flags.stop_requested = False

    async def cancelled_process_one_file(_self, _task):
        raise scraper_module.asyncio.CancelledError

    monkeypatch.setattr(scraper_module.Scraper, "process_one_file", cancelled_process_one_file)

    scraper = scraper_module.Scraper(crawler_provider=object())
    with pytest.raises(scraper_module.UnexpectedScrapeCancellation, match="异常取消"):
        await scraper._run_tasks_with_limit([Path("MIAA-001.mp4")], 1, 1)


def test_save_remain_list_retries_when_tasks_change_during_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from mdcx.base import file as file_module
    from mdcx.config.enums import Switch

    remain_path = tmp_path / "remain.txt"
    first = Path("MIAA-001.mp4")
    second = Path("MIAA-002.mp4")
    Flags.replace_remain_list([first, second])
    monkeypatch.setattr(file_module.resources, "u", lambda _name: remain_path)
    monkeypatch.setattr(file_module.manager.config, "switch_on", [Switch.REMAIN_TASK])

    original_replace = file_module.os.replace
    replace_count = 0

    def mutate_before_replace(source: Path, target: Path):
        nonlocal replace_count
        replace_count += 1
        if replace_count == 1:
            assert Flags.remove_remain_path(first)
        original_replace(source, target)

    monkeypatch.setattr(file_module.os, "replace", mutate_before_replace)

    file_module.save_remain_list()
    assert Flags.can_save_remain is True

    file_module.save_remain_list()
    assert remain_path.read_text(encoding="utf-8") == f"{second}\n"
    assert Flags.can_save_remain is False


def test_concurrent_remain_saves_serialize_and_keep_latest_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import threading

    from mdcx.base import file as file_module
    from mdcx.config.enums import Switch

    remain_path = tmp_path / "remain.txt"
    old_path = Path("MIAA-OLD.mp4")
    new_path = Path("MIAA-NEW.mp4")
    Flags.replace_remain_list([old_path])
    monkeypatch.setattr(file_module.resources, "u", lambda _name: remain_path)
    monkeypatch.setattr(file_module.manager.config, "switch_on", [Switch.REMAIN_TASK])

    original_replace = file_module.os.replace
    first_at_replace = threading.Event()
    second_at_replace = threading.Event()
    release_first = threading.Event()

    def controlled_replace(source: Path, target: Path):
        if threading.current_thread().name == "remain-save-first":
            first_at_replace.set()
            assert release_first.wait(timeout=1)
        else:
            second_at_replace.set()
        original_replace(source, target)

    monkeypatch.setattr(file_module.os, "replace", controlled_replace)
    first_save = threading.Thread(target=file_module.save_remain_list, name="remain-save-first")
    second_save = threading.Thread(target=file_module.save_remain_list, name="remain-save-second")

    first_save.start()
    assert first_at_replace.wait(timeout=1)
    Flags.replace_remain_list([new_path])
    second_save.start()
    overlapped = second_at_replace.wait(timeout=0.1)
    release_first.set()
    first_save.join(timeout=1)
    second_save.join(timeout=1)

    assert not overlapped
    assert not first_save.is_alive()
    assert not second_save.is_alive()
    assert remain_path.read_text(encoding="utf-8") == f"{new_path}\n"
    assert Flags.can_save_remain is False
