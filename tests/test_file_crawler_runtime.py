import pytest

from mdcx.config.enums import FixedScrapingType, Website
from mdcx.config.models import Config
from mdcx.core.file_crawler import FileScraper
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.enums import FileMode
from mdcx.models.log_buffer import LogBuffer
from mdcx.models.types import CrawlerInput, CrawlTask
from tests.file_crawler_test_support import (
    FakeConfig,
    FakeCrawlerProvider,
    RecordingCrawler,
    RecordingCrawlerProvider,
    ResultRecordingCrawler,
    ResultRecordingCrawlerProvider,
    build_result,
)


@pytest.mark.asyncio
async def test_speed_mode_uses_first_successful_type_site_without_field_merge():
    records: list[Website] = []
    provider = ResultRecordingCrawlerProvider(
        {
            Website.AVBASE: ResultRecordingCrawler(
                Website.AVBASE, records, build_result(Website.AVBASE, runtime="120")
            ),
            Website.JAVDB: ResultRecordingCrawler(Website.JAVDB, records, build_result(Website.JAVDB, runtime="55")),
        }
    )
    config = Config(scrape_like="speed", website_youma=[Website.AVBASE, Website.JAVDB])
    config.set_field_sites(CrawlerResultFields.RUNTIME, [Website.JAVDB, Website.AVBASE])
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "SCUTE-1354"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.runtime == "120"
    assert result.field_sources[CrawlerResultFields.TITLE] == Website.AVBASE.value
    assert records == [Website.AVBASE]


@pytest.mark.asyncio
async def test_speed_mode_falls_back_to_next_site_after_empty_result():
    records: list[Website] = []
    provider = ResultRecordingCrawlerProvider(
        {
            Website.AVBASE: ResultRecordingCrawler(Website.AVBASE, records, None),
            Website.JAVDB: ResultRecordingCrawler(Website.JAVDB, records, build_result(Website.JAVDB, runtime="55")),
        }
    )
    config = Config(scrape_like="speed", website_youma=[Website.AVBASE, Website.JAVDB])
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "SCUTE-1354"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.runtime == "55"
    assert result.field_sources[CrawlerResultFields.TITLE] == Website.JAVDB.value
    assert records == [Website.AVBASE, Website.JAVDB]


@pytest.mark.asyncio
async def test_uncensored_fdd_task_reaches_configured_uncensored_crawler():
    records: list[Website] = []
    provider = ResultRecordingCrawlerProvider(
        {
            Website.AVSOX: ResultRecordingCrawler(Website.AVSOX, records, build_result(Website.AVSOX)),
            Website.JAVBUS: ResultRecordingCrawler(Website.JAVBUS, records, build_result(Website.JAVBUS)),
        }
    )
    config = Config(scrape_like="speed", website_wuma=[Website.AVSOX, Website.JAVBUS])
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "FDD-2007"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.scraping_type == FixedScrapingType.WUMA
    assert result.mosaic == "无码"
    assert records == [Website.AVSOX]


@pytest.mark.asyncio
async def test_call_crawler_restore_number_for_mgstage():
    records: list[tuple[str, str]] = []
    provider = RecordingCrawlerProvider(
        {
            Website.DMM: RecordingCrawler(Website.DMM, records),
            Website.MGSTAGE: RecordingCrawler(Website.MGSTAGE, records),
        }
    )
    scraper = FileScraper(FakeConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "200GANA-3327"
    task_input.short_number = "GANA-3327"

    await scraper._call_crawler(task_input, Website.DMM)
    assert task_input.number == "200GANA-3327"

    await scraper._call_crawler(task_input, Website.MGSTAGE)
    assert task_input.number == "200GANA-3327"

    assert records == [
        (Website.DMM.value, "GANA-3327"),
        (Website.MGSTAGE.value, "200GANA-3327"),
    ]


@pytest.mark.asyncio
async def test_call_crawler_restore_number_when_exception():
    records: list[tuple[str, str]] = []
    provider = RecordingCrawlerProvider(
        {
            Website.DMM: RecordingCrawler(Website.DMM, records, should_raise=True),
        }
    )
    scraper = FileScraper(FakeConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "200GANA-3327"
    task_input.short_number = "GANA-3327"

    with pytest.raises(RuntimeError, match="boom"):
        await scraper._call_crawler(task_input, Website.DMM)

    assert task_input.number == "200GANA-3327"
    assert records == [(Website.DMM.value, "GANA-3327")]


@pytest.mark.asyncio
async def test_call_specific_crawler_writes_debug_error_to_log_buffer():
    LogBuffer.error().clear()
    provider = FakeCrawlerProvider({Website.THEPORNDB: (None, RuntimeError("请添加 API Token 后刮削！"))})
    scraper = FileScraper(FakeConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "Nurumassage.26.02.23"

    result = await scraper._call_specific_crawler(task_input, Website.THEPORNDB)

    assert result is None
    assert "请添加 API Token 后刮削！" in LogBuffer.error().get()
    LogBuffer.error().clear()
