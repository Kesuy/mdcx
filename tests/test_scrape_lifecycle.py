import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcx.core import scraper as module
from mdcx.models.enums import FileMode


@pytest.mark.asyncio
async def test_stop_waits_for_work_provider_and_save_before_allowing_restart(monkeypatch):
    working = asyncio.Event()
    release_work = asyncio.Event()
    closing = asyncio.Event()
    release_close = asyncio.Event()
    saving = asyncio.Event()
    release_save = asyncio.Event()
    resets = []

    async def work(self, *_):
        working.set()
        await release_work.wait()

    async def close():
        closing.set()
        await release_close.wait()

    async def save():
        saving.set()
        await release_save.wait()

    monkeypatch.setattr(module.Scraper, "_run", work)
    monkeypatch.setattr(module, "save_success_list", save)
    monkeypatch.setattr(
        module,
        "signal",
        SimpleNamespace(
            reset_buttons_status=SimpleNamespace(emit=lambda: resets.append(True)),
            show_log_text=lambda _: None,
        ),
    )
    scraper = module.Scraper(SimpleNamespace(close=close))
    monkeypatch.setattr(module, "_active_scraper", scraper)
    run = asyncio.create_task(module._run_active_scrape(scraper, FileMode.Default, []))
    await working.wait()
    stop = asyncio.create_task(module.stop_active_scrape())
    await asyncio.sleep(0)
    assert scraper.session.cancellation_requested
    try:
        for entered, release in [(working, release_work), (closing, release_close), (saving, release_save)]:
            await asyncio.wait_for(entered.wait(), 1)
            assert not stop.done()
            assert not scraper.finished.done()
            module.start_new_scrape(FileMode.Single, [Path("next.mp4")])
            assert module._active_scraper is scraper
            release.set()
        await asyncio.wait_for(stop, 1)
        await run
        assert module._active_scraper is None
        assert not resets  # The stop controller restores UI only after this acknowledgement.
    finally:
        release_work.set()
        release_close.set()
        release_save.set()
        await asyncio.gather(run, stop, return_exceptions=True)


@pytest.mark.asyncio
async def test_stop_does_not_cancel_inflight_file_or_schedule_next_file():
    scraper = module.Scraper(object())
    entered = asyncio.Event()
    release = asyncio.Event()
    completed = []

    async def process(task):
        entered.set()
        await release.wait()
        completed.append(task[0])

    scraper.process_one_file = process
    files = [Path("one.mp4"), Path("two.mp4")]
    run = asyncio.create_task(scraper._run_tasks_with_limit(files, 2, 1))
    await entered.wait()
    scraper.session.request_cancel()
    release.set()
    await asyncio.wait_for(run, 1)
    assert completed == files[:1]


@pytest.mark.asyncio
async def test_completion_closes_provider_before_restoring_buttons_on_error(monkeypatch):
    events = []

    async def work(self, *_):
        raise RuntimeError("failed")

    async def close():
        events.append("close")

    async def save():
        events.append("save")

    monkeypatch.setattr(module.Scraper, "_run", work)
    monkeypatch.setattr(module, "save_success_list", save)
    monkeypatch.setattr(
        module,
        "signal",
        SimpleNamespace(
            show_traceback_log=lambda _: None,
            show_log_text=lambda _: None,
            reset_buttons_status=SimpleNamespace(emit=lambda: events.append("reset")),
        ),
    )
    scraper = module.Scraper(SimpleNamespace(close=close))
    monkeypatch.setattr(module, "_active_scraper", scraper)
    await module._run_active_scrape(scraper, FileMode.Default, [])
    assert events == ["close", "save", "reset"]
    assert scraper.finished.done()
    assert module._active_scraper is None


@pytest.mark.asyncio
async def test_stop_requested_before_start_is_preserved(monkeypatch):
    events = []

    async def close():
        events.append("close")

    async def save():
        events.append("save")

    monkeypatch.setattr(module, "save_success_list", save)
    scraper = module.Scraper(SimpleNamespace(close=close))
    scraper.session.request_cancel()
    monkeypatch.setattr(module, "_active_scraper", scraper)
    # The real _run must return before scanning files, without clearing cancellation.
    await module._run_active_scrape(scraper, FileMode.Default, [])
    assert scraper.session.cancellation_requested
    assert events == ["close", "save"]
    assert scraper.finished.done()
