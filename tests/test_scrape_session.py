from pathlib import Path

from mdcx.models.enums import FileMode
from mdcx.models.failure import FailureCategory, FailureRecord
from mdcx.models.flags import Flags
from mdcx.models.session import ScrapeSession


def test_scrape_sessions_keep_run_state_isolated():
    first = ScrapeSession()
    second = ScrapeSession()
    first.reset(FileMode.Default)
    second.reset(FileMode.Single)

    first.replace_remain_queue([Path("A.mp4"), Path("B.mp4")])
    first.sync_progress(total=2, started=1, completed=1, succeeded=1)
    first.scrape_results["A"] = object()  # type: ignore[assignment]
    first.record_failure(FailureRecord(Path("B.mp4"), "crawl", FailureCategory.NETWORK, "timeout", True))
    first.request_cancel()

    assert first.cancellation_requested
    assert first.state.success_count == 1
    assert first.state.failure_count == 1
    assert first.remain_snapshot()[0] == [Path("A.mp4"), Path("B.mp4")]
    assert not second.cancellation_requested
    assert second.state.file_mode is FileMode.Single
    assert second.state.failures == []
    assert second.scrape_results == {}


def test_flags_remain_adapter_delegates_to_the_bound_session():
    Flags.reset()
    session = ScrapeSession()
    session.replace_remain_queue([Path("A.mp4")])
    Flags.bind_session(session)

    assert Flags.remove_remain_path(Path("A.mp4"))
    assert session.remain_snapshot()[0] == []
    assert Flags.remain_snapshot()[0] == []


def test_flags_per_run_caches_are_session_owned_aliases():
    Flags.reset()
    session = ScrapeSession()
    Flags.bind_session(session)

    Flags.json_get_status["ABP-001"] = True
    Flags.pic_catch_set.add(Path("poster.jpg"))

    assert session.cache("json_get_status") == {"ABP-001": True}
    assert session.cache("pic_catch_set", set) == {Path("poster.jpg")}
