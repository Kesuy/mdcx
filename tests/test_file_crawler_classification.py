from pathlib import Path

import pytest

from mdcx.config.enums import FixedScrapingType, Language, Website
from mdcx.config.models import Config
from mdcx.core.file_crawler import (
    FileScraper,
    _deal_res,
    _is_suren_number,
    classify_existing_scrape_result,
    classify_scrape_task,
)
from mdcx.core.translate import AVWIKI_SCRAPING_TYPES, _should_query_avwiki_actor
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.types import CrawlersResult, CrawlTask
from tests.file_crawler_test_support import ClassificationConfig, FakeCrawlerProvider


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", True),
        ("00", True),
        ("0.0", True),
        ("0.00", True),
        ("55", False),
        ("", False),
    ],
)
def test_is_invalid_runtime(value: str, expected: bool):
    assert FileScraper._is_invalid_runtime(value) is expected


def test_deal_res_normalize_iso_release():
    result = CrawlersResult.empty()
    result.release = "2023-07-14T01:00:00Z"

    normalized = _deal_res(result)

    assert normalized.release == "2023-07-14"


@pytest.mark.parametrize(
    ("file_number", "short_number", "expected"),
    [
        ("259LUXU-1488", "LUXU-1488", True),
        ("435MFC-142", "MFC-142", True),
        ("SIRO-5533", "", True),
        ("SSIS-001", "", False),
        ("FC2-123456", "", False),
    ],
)
def test_is_suren_number_matches_current_scrape_branch(file_number: str, short_number: str, expected: bool):
    assert _is_suren_number(file_number, short_number) is expected


@pytest.mark.parametrize(
    ("number", "mosaic", "short_number", "expected_type", "expected_sites"),
    [
        ("259LUXU-1488", "", "LUXU-1488", FixedScrapingType.SUREN, {Website.MGSTAGE}),
        ("SIRO-5533", "", "", FixedScrapingType.SUREN, {Website.MGSTAGE}),
        ("FC2-123456", "", "", FixedScrapingType.FC2, {Website.FC2}),
        ("100225_100", "无码", "", FixedScrapingType.WUMA, {Website.JAVBUS}),
        ("100225_101", "無修正", "", FixedScrapingType.WUMA, {Website.JAVBUS}),
        ("ABF-131", "无码破解", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("ABF-132", "无码流出", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("ABF-133", "流出", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("ABF-134", "無碼破解", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("ABF-135", "無碼流出", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("ABF-136", "无码流出", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("HEYZO-3843", "", "", FixedScrapingType.WUMA, {Website.JAVBUS}),
        ("FDD-2007", "", "", FixedScrapingType.WUMA, {Website.JAVBUS}),
        ("FZ65", "", "", FixedScrapingType.WUMA, {Website.JAVBUS}),
        ("MD-1234", "", "", FixedScrapingType.GUOCHAN, {Website.MDTV}),
        ("DANDY-732", "", "", FixedScrapingType.YOUMA, {Website.DMM}),
        ("SSNI00321", "", "", FixedScrapingType.YOUMA, {Website.DMM}),
    ],
)
def test_classify_scrape_task_keeps_existing_type_branches(
    number: str,
    mosaic: str,
    short_number: str,
    expected_type: FixedScrapingType,
    expected_sites: set[Website],
):
    task = CrawlTask.empty()
    task.number = number
    task.mosaic = mosaic
    task.short_number = short_number

    classification = classify_scrape_task(task, ClassificationConfig())

    assert classification.scraping_type == expected_type
    assert classification.scraping_type_source == "auto"
    assert classification.sites == expected_sites


@pytest.mark.parametrize(
    ("number", "file_path", "expected_website"),
    [
        ("KIN8-4188", "", Website.KIN8),
        ("MYWIFE-1500", "D:/test/mywife/MYWIFE-1500.mp4", Website.MYWIFE),
    ],
)
def test_classify_scrape_task_marks_youma_specific_crawlers(number: str, file_path: str, expected_website: Website):
    task = CrawlTask.empty()
    task.number = number
    if file_path:
        task.file_path = Path(file_path)

    classification = classify_scrape_task(task, ClassificationConfig())

    assert classification.scraping_type == FixedScrapingType.YOUMA
    assert classification.website == expected_website


def test_classify_existing_scrape_result_uses_nfo_mosaic_without_substring_wuma_match():
    task = CrawlTask.empty()
    task.number = "ABF-131"

    result = CrawlersResult.empty()
    result.number = "ABF-131"
    result.mosaic = "无码破解"

    classification = classify_existing_scrape_result(task, result, ClassificationConfig())

    assert classification.scraping_type == FixedScrapingType.YOUMA
    assert result.scraping_type == FixedScrapingType.YOUMA
    assert result.scraping_type_source == "auto"


def test_classify_scrape_task_fixed_type_overrides_auto_detection():
    class FixedSurenConfig(ClassificationConfig):
        fixed_scraping_type = FixedScrapingType.SUREN

    task = CrawlTask.empty()
    task.number = "DANDY-732"

    classification = classify_scrape_task(task, FixedSurenConfig())

    assert classification.scraping_type == FixedScrapingType.SUREN
    assert classification.scraping_type_source == "fixed"
    assert classification.sites == {Website.MGSTAGE}


def test_avwiki_uses_unified_scraping_types():
    assert AVWIKI_SCRAPING_TYPES == {
        FixedScrapingType.YOUMA,
        FixedScrapingType.SUREN,
        FixedScrapingType.FC2,
    }


@pytest.mark.parametrize(
    ("website", "expected_language", "expected_org_language"),
    [
        (Website.AIRAV_CC, Language.ZH_CN, Language.ZH_CN),
        (Website.IQQTV, Language.ZH_CN, Language.ZH_CN),
        (Website.JAVLIBRARY, Language.ZH_CN, Language.ZH_CN),
        (Website.MDTV, Language.ZH_CN, Language.ZH_CN),
        (Website.DMM, Language.JP, Language.ZH_CN),
    ],
)
def test_specific_crawler_language_uses_website_enum_members(
    website: Website, expected_language: Language, expected_org_language: Language
):
    config = Config()
    config.set_field_language(CrawlerResultFields.TITLE, Language.ZH_CN)
    scraper = FileScraper(config, FakeCrawlerProvider({}))

    assert scraper._get_specific_crawler_language(website) == (expected_language, expected_org_language)


@pytest.mark.parametrize(
    ("scraping_type", "actors", "expected"),
    [
        (FixedScrapingType.YOUMA, [], True),
        (FixedScrapingType.YOUMA, ["未知演员"], True),
        (FixedScrapingType.YOUMA, ["葵つかさ"], False),
        (FixedScrapingType.SUREN, ["素人"], True),
        (FixedScrapingType.FC2, ["販売者"], True),
        (FixedScrapingType.WUMA, [], False),
    ],
)
def test_avwiki_youma_only_queries_when_actor_unknown_or_empty(
    scraping_type: FixedScrapingType, actors: list[str], expected: bool
):
    result = CrawlersResult.empty()
    result.scraping_type = scraping_type
    result.actors = actors

    assert _should_query_avwiki_actor(result) is expected
