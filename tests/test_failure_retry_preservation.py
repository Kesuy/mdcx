from pathlib import Path

from mdcx.core import scraper as scraper_module
from mdcx.core.scraper import Scraper
from mdcx.models.failure import FailureCategory, FailureRecord
from mdcx.models.flags import Flags
from mdcx.models.session import ScrapeSession


def test_targeted_retry_restores_unselected_failures_after_retry_run(monkeypatch):
    preserved = FailureRecord(
        Path("A.mp4"),
        "crawl",
        FailureCategory.AUTHENTICATION,
        "cookie expired",
        False,
    )
    new_failure = FailureRecord(
        Path("B.mp4"),
        "crawl",
        FailureCategory.NETWORK,
        "timeout",
        True,
    )
    session = ScrapeSession()
    session.state.failures.append(new_failure)
    Flags.failed_list = [new_failure.legacy_tuple()]
    emitted: list[str] = []
    monkeypatch.setattr(scraper_module.signal.view_failed_list_settext, "emit", emitted.append)

    scraper = Scraper(
        object(),
        session=session,
        services=object(),
        preserved_failures=[preserved],
    )
    scraper._restore_preserved_failures()

    assert session.state.failures == [preserved, new_failure]
    assert Flags.failed_records is session.state.failures
    assert Flags.failed_list == [preserved.legacy_tuple(), new_failure.legacy_tuple()]
    assert emitted == ["失败 2"]
    assert scraper.preserved_failures == []


def test_targeted_retry_does_not_duplicate_preserved_path_that_failed_again(monkeypatch):
    preserved = FailureRecord(
        Path("A.mp4"),
        "crawl",
        FailureCategory.NETWORK,
        "first timeout",
        True,
    )
    failed_again = FailureRecord(
        Path("A.mp4"),
        "crawl",
        FailureCategory.NETWORK,
        "second timeout",
        True,
    )
    session = ScrapeSession()
    session.state.failures.append(failed_again)
    Flags.failed_list = [failed_again.legacy_tuple()]
    monkeypatch.setattr(scraper_module.signal.view_failed_list_settext, "emit", lambda _text: None)

    scraper = Scraper(
        object(),
        session=session,
        services=object(),
        preserved_failures=[preserved],
    )
    scraper._restore_preserved_failures()

    assert session.state.failures == [failed_again]
    assert Flags.failed_list == [failed_again.legacy_tuple()]
