from pathlib import Path

import pytest

from mdcx.models.failure import FailureCategory, classify_failure


@pytest.mark.parametrize(
    ("message", "stage", "category", "retryable"),
    [
        ("request timeout", "crawl", FailureCategory.NETWORK, True),
        ("Cookie 已过期", "crawl", FailureCategory.AUTHENTICATION, False),
        ("search no result", "search", FailureCategory.SEARCH_NO_RESULT, True),
        ("parser selector missing", "crawl", FailureCategory.PARSER, False),
        ("poster image download failed", "image", FailureCategory.IMAGE_DOWNLOAD, True),
        ("WinError 5 permission denied", "file", FailureCategory.FILE_IO, True),
        ("move target conflict", "move", FailureCategory.RENAME_MOVE, False),
        ("NFO metadata invalid", "metadata", FailureCategory.METADATA, False),
    ],
)
def test_failure_classification_is_structured(message, stage, category, retryable):
    record = classify_failure(Path("movie.mp4"), message, stage=stage, site="javdb")

    assert record.category is category
    assert record.retryable is retryable
    assert record.site == "javdb"
    assert record.legacy_tuple() == (Path("movie.mp4"), message)


def test_programming_error_is_not_misclassified_from_message_keywords():
    error = AttributeError("connection attribute missing")

    record = classify_failure(Path("movie.mp4"), str(error), exception=error)

    assert record.category is FailureCategory.INTERNAL_ERROR
    assert record.retryable is False


def test_rename_target_conflict_requires_user_intervention():
    record = classify_failure(Path("movie.mp4"), "move target conflict", stage="move")

    assert record.category is FailureCategory.RENAME_MOVE
    assert record.retryable is False
