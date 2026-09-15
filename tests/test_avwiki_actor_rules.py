import pytest

from mdcx.config.enums import FixedScrapingType, Switch
from mdcx.config.manager import manager
from mdcx.core.avwiki_rules import (
    is_avwiki_mgs_amateur_metadata,
    is_avwiki_mgs_amateur_number,
)
from mdcx.core.translate import _should_query_avwiki_actor
from mdcx.models.types import CrawlersResult


@pytest.fixture(autouse=True)
def restore_switches():
    previous = manager.config.switch_on.copy()
    manager.config.switch_on = [value for value in previous if value != Switch.FORCE_AVWIKI_ACTOR]
    yield
    manager.config.switch_on = previous


def _result(
    number: str,
    *,
    scraping_type: FixedScrapingType = FixedScrapingType.YOUMA,
    actor: str = "演员名",
    studio: str = "",
    publisher: str = "",
    series: str = "",
) -> CrawlersResult:
    result = CrawlersResult.empty()
    result.number = number
    result.scraping_type = scraping_type
    result.actors = [actor] if actor else []
    result.all_actors = result.actors.copy()
    result.studio = studio
    result.publisher = publisher
    result.series = series
    return result


@pytest.mark.parametrize(
    "number",
    [
        "MFCW-023",
        "MFCW-028",
        "MMNM-039",
        "SIMH-009",
        "SIMF-007",
        "SIMW-011",
        "MFCS-223",
        "DDH-448",
        "ORECZ-673",
        "OREMO-611",
        "ORESL-002",
        "OREV-170",
    ],
)
def test_known_mgs_amateur_short_numbers_trigger_avwiki(number: str):
    assert is_avwiki_mgs_amateur_number(number)
    assert _should_query_avwiki_actor(_result(number))


@pytest.mark.parametrize("number", ["SSIS-001", "MIDV-123", "IPZZ-123", "JUL-999"])
def test_normal_youma_with_known_actor_does_not_add_avwiki_request(number: str):
    assert not is_avwiki_mgs_amateur_number(number)
    assert not _should_query_avwiki_actor(_result(number))


def test_existing_suren_behavior_is_preserved():
    result = _result("300MIUM-1431", scraping_type=FixedScrapingType.SUREN)
    assert _should_query_avwiki_actor(result)


def test_empty_youma_actor_preserves_existing_fallback():
    result = _result("SSIS-001", actor="")
    assert _should_query_avwiki_actor(result)


@pytest.mark.parametrize(
    "field_value",
    [
        "MOON FORCE WIFE",
        "しろうとまんまん沼",
        "ドキュメントdeハメハメ",
        "街角シロウトナンパ+",
        "俺の素人 - ORECZ",
    ],
)
def test_mgs_amateur_metadata_catches_future_short_prefixes(field_value: str):
    assert is_avwiki_mgs_amateur_metadata(field_value)
    result = _result("NEWCODE-001", series=field_value)
    assert _should_query_avwiki_actor(result)


def test_force_switch_queries_all_scraping_types():
    manager.config.switch_on = [*manager.config.switch_on, Switch.FORCE_AVWIKI_ACTOR]
    result = _result("HEYZO-1234", scraping_type=FixedScrapingType.WUMA)
    assert _should_query_avwiki_actor(result)
