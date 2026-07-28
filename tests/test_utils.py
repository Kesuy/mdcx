import asyncio
import threading
import time
from concurrent.futures import CancelledError

import pytest

from mdcx.utils import (
    AsyncBackgroundExecutor,
    add_html_plain_text,
    clean_list,
    collapse_inline_script_splits,
    kill_a_thread,
)
from mdcx.utils.language import is_english, is_japanese, is_probably_english_for_translation


@pytest.mark.parametrize(
    "s,expected",
    [
        ("", False),
        ("こんにちは", True),
        ("カタカナ", True),
        ("abc123", False),
        ("テスト123", True),
        ("Hello世界", False),
    ],
)
def test_is_japanese(s, expected):
    assert is_japanese(s) == expected


@pytest.mark.parametrize(
    "s,expected",
    [
        ("", False),
        ("Hello, world!", True),
        ("1234567890", True),
        ("This is a test.", True),
        ("こんにちは", False),
        ("テスト123", False),
        ("中文", False),
        ("abc@#%&*()", True),
        ("abc中文", False),
    ],
)
def test_is_english(s, expected):
    assert is_english(s) == expected


@pytest.mark.parametrize(
    "s,expected",
    [
        ("a,b,a,c", "a,b,c"),
        ("a,b,c", "a,b,c"),
        (" a ,b, a,c ", "a,b,c"),
        ("", ""),
        ("a,,b", "a,b"),
        ("A,a,B,b", "A,a,B,b"),
    ],
)
def test_clean_list(s, expected):
    assert clean_list(s) == expected


def test_background_executor_starts_lazily():
    executor = AsyncBackgroundExecutor()

    assert executor._thread is None
    assert executor._loop is None

    future = executor.submit(asyncio.sleep(0, result="ok"))

    assert future.result(timeout=5) == "ok"
    assert executor._thread is not None
    assert executor._thread.is_alive()
    executor._stop_background_thread()


def test_background_executor_cancels_only_requested_group():
    executor = AsyncBackgroundExecutor()
    scrape_started = threading.Event()
    maintenance_started = threading.Event()
    ungrouped_started = threading.Event()
    scrape_finished = threading.Event()
    maintenance_finished = threading.Event()
    ungrouped_finished = threading.Event()

    async def wait_forever(started: threading.Event, finished: threading.Event):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    scrape_future = executor.submit(wait_forever(scrape_started, scrape_finished), group="scrape")
    maintenance_future = executor.submit(wait_forever(maintenance_started, maintenance_finished), group="maintenance")
    ungrouped_future = executor.submit(wait_forever(ungrouped_started, ungrouped_finished))
    try:
        assert scrape_started.wait(timeout=1)
        assert maintenance_started.wait(timeout=1)
        assert ungrouped_started.wait(timeout=1)

        executor.cancel_async(group="scrape")

        with pytest.raises(CancelledError):
            scrape_future.result(timeout=1)
        assert scrape_finished.wait(timeout=1)
        assert not maintenance_future.done()
        assert not ungrouped_future.done()
    finally:
        executor.cancel()
        for future in (scrape_future, maintenance_future, ungrouped_future):
            with pytest.raises(CancelledError):
                future.result(timeout=1)
        assert maintenance_finished.wait(timeout=1)
        assert ungrouped_finished.wait(timeout=1)
        executor._stop_background_thread()


@pytest.mark.parametrize("outcome", ["completed", "failed", "cancelled"])
def test_background_executor_cleans_pending_and_group_for_every_outcome(outcome: str):
    executor = AsyncBackgroundExecutor()
    started = threading.Event()
    finished = threading.Event()

    async def task():
        started.set()
        try:
            if outcome == "completed":
                return "done"
            if outcome == "failed":
                raise RuntimeError("expected failure")
            await asyncio.Event().wait()
        finally:
            finished.set()

    future = executor.submit(task(), group="outcome")
    try:
        assert started.wait(timeout=1)
        if outcome == "completed":
            assert future.result(timeout=1) == "done"
        elif outcome == "failed":
            with pytest.raises(RuntimeError, match="expected failure"):
                future.result(timeout=1)
        else:
            future.cancel()
            with pytest.raises(CancelledError):
                future.result(timeout=1)
        assert finished.wait(timeout=1)
        assert future not in executor._pending_futures
        assert future not in executor._future_groups
    finally:
        executor.cancel()
        executor._stop_background_thread()


def test_background_executor_fast_future_does_not_remain_pending():
    executor = AsyncBackgroundExecutor()
    try:
        futures = [executor.submit(asyncio.sleep(0, result=index), group="fast") for index in range(100)]
        assert [future.result(timeout=1) for future in futures] == list(range(100))
        assert executor._pending_futures == set()
        assert executor._future_groups == {}
    finally:
        executor.cancel()
        executor._stop_background_thread()


def test_kill_a_thread_waits_boundedly_without_forcing_thread_exit():
    release = threading.Event()
    thread = threading.Thread(target=release.wait)
    thread.start()

    try:
        started_at = time.monotonic()
        stopped = kill_a_thread(thread, timeout=0.02)

        assert stopped is False
        assert time.monotonic() - started_at < 0.2
        assert thread.is_alive()
    finally:
        release.set()
        thread.join(timeout=1)
    assert not thread.is_alive()


def test_collapse_inline_script_splits_recovers_streamed_text():
    text = 'https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=dvdms674/?i3_"])</script><script>self.__next_f.push([1,"ref=search\\u0026i3_ord=6'
    assert (
        collapse_inline_script_splits(text)
        == "https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=dvdms674/?i3_ref=search\\u0026i3_ord=6"
    )


def test_add_html_plain_text_escapes_script_like_content_and_keeps_full_message():
    text = (
        'GET https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=dvdms674/?i3_"])'
        '</script><script>self.__next_f.push([1,"ref=search&i3_ord=6'
    )
    rendered = add_html_plain_text(text)

    assert "&lt;/script&gt;&lt;script&gt;" in rendered
    assert "self.__next_f.push([1,&quot;ref=search&amp;i3_ord=6" in rendered
    assert '<a href="https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=dvdms674/?i3_' in rendered


@pytest.mark.parametrize(
    "s,expected",
    [
        ("", False),
        ("Youngermommy.24.11.09", True),
        ("Ricky Spanish is on the phone with his friend.", True),
        ("Scarlett’s fantasy gets wild — and explicit.", True),
        ("これは日本語の文章です。", False),
        ("中文简介内容", False),
        ("abc 中文 mixed", False),
    ],
)
def test_is_probably_english_for_translation(s, expected):
    assert is_probably_english_for_translation(s) == expected
