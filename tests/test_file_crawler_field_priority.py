import pytest

from mdcx.config.enums import DownloadableFile, Website
from mdcx.config.models import Config
from mdcx.core.file_crawler import FileScraper, classify_scrape_task
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.manual import ManualConfig
from mdcx.models.enums import FileMode
from mdcx.models.types import CrawlerInput, CrawlTask
from tests.file_crawler_test_support import (
    FakeConfig,
    FakeCrawlerProvider,
    Fc2PosterPriorityConfig,
    ImagePriorityConfig,
    ResultRecordingCrawler,
    ResultRecordingCrawlerProvider,
    TypePriorityConfig,
    build_image_result,
    build_result,
)


@pytest.mark.asyncio
async def test_call_crawlers_runtime_skip_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.RUNTIME,))

    provider = FakeCrawlerProvider(
        {
            Website.AVBASE: build_result(Website.AVBASE, "0"),
            Website.JAVDB: build_result(Website.JAVDB, "55"),
        }
    )
    scraper = FileScraper(FakeConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "SCUTE-1354"

    result = await scraper._call_crawlers(task_input, {Website.AVBASE, Website.JAVDB})

    assert result is not None
    assert result.runtime == "55"
    assert result.field_sources[CrawlerResultFields.RUNTIME] == Website.JAVDB.value
    provenance = result.get_provenance(CrawlerResultFields.RUNTIME)
    assert provenance is not None
    assert provenance.source == Website.JAVDB.value
    assert provenance.priority_chain == (Website.AVBASE.value, Website.JAVDB.value)


@pytest.mark.asyncio
async def test_call_crawlers_release_skip_invalid_and_fill_year(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.RELEASE,))

    provider = FakeCrawlerProvider(
        {
            Website.AVBASE: build_result(Website.AVBASE, release="0000-00-00"),
            Website.JAVDB: build_result(Website.JAVDB, release="2024-1-2"),
        }
    )
    scraper = FileScraper(FakeConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "SIRO-5533"

    result = await scraper._call_crawlers(task_input, {Website.AVBASE, Website.JAVDB})

    assert result is not None
    assert result.release == "2024-01-02"
    assert result.year == "2024"
    assert result.field_sources[CrawlerResultFields.RELEASE] == Website.JAVDB.value


@pytest.mark.asyncio
async def test_call_crawlers_uses_type_field_priority(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.RUNTIME,))

    provider = FakeCrawlerProvider(
        {
            Website.AVBASE: build_result(Website.AVBASE, "120"),
            Website.JAVDB: build_result(Website.JAVDB, "55"),
        }
    )
    scraper = FileScraper(TypePriorityConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "SCUTE-1354"

    result = await scraper._call_crawlers(
        task_input,
        classification=classify_scrape_task(task_input, Config(website_youma=[Website.AVBASE, Website.JAVDB])),
    )

    assert result is not None
    assert result.runtime == "55"
    assert result.field_sources[CrawlerResultFields.RUNTIME] == Website.JAVDB.value


@pytest.mark.asyncio
async def test_call_crawlers_legacy_site_list_uses_global_field_priority(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.RUNTIME,))

    provider = FakeCrawlerProvider(
        {
            Website.AVBASE: build_result(Website.AVBASE, "120"),
            Website.JAVDB: build_result(Website.JAVDB, "55"),
        }
    )
    config = Config(website_youma=[Website.AVBASE, Website.JAVDB])
    config.set_field_sites(CrawlerResultFields.RUNTIME, [Website.JAVDB, Website.AVBASE])
    scraper = FileScraper(config, provider)
    task_input = CrawlerInput.empty()
    task_input.number = "SCUTE-1354"

    result = await scraper._call_crawlers(task_input, {Website.AVBASE, Website.JAVDB})

    assert result is not None
    assert result.runtime == "55"
    assert result.field_sources[CrawlerResultFields.RUNTIME] == Website.JAVDB.value


@pytest.mark.asyncio
async def test_call_crawlers_collects_all_image_candidates_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.POSTER, CrawlerResultFields.THUMB))

    provider = FakeCrawlerProvider(
        {
            Website.AVBASE: build_image_result(
                Website.AVBASE,
                poster="https://example.test/avbase-poster.jpg",
                thumb="https://example.test/avbase-thumb.jpg",
                image_download=False,
            ),
            Website.JAVDB: build_image_result(
                Website.JAVDB,
                poster="https://example.test/javdb-poster.jpg",
                thumb="https://example.test/javdb-thumb.jpg",
                image_download=True,
            ),
        }
    )
    scraper = FileScraper(ImagePriorityConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "SCUTE-1354"

    result = await scraper._call_crawlers(
        task_input,
        classification=classify_scrape_task(task_input, Config(website_youma=[Website.AVBASE, Website.JAVDB])),
    )

    assert result is not None
    assert result.poster == "https://example.test/avbase-poster.jpg"
    assert result.poster_from == Website.AVBASE.value
    assert result.get_provenance(CrawlerResultFields.POSTER).source == Website.AVBASE.value
    assert result.get_provenance("fanart").source == Website.AVBASE.value
    assert result.poster_list == [
        (Website.AVBASE.value, "https://example.test/avbase-poster.jpg", False),
        (Website.JAVDB.value, "https://example.test/javdb-poster.jpg", True),
    ]
    assert result.thumb_list == [
        (Website.AVBASE.value, "https://example.test/avbase-thumb.jpg"),
        (Website.JAVDB.value, "https://example.test/javdb-thumb.jpg"),
    ]


@pytest.mark.asyncio
async def test_call_crawlers_collects_poster_candidates_only_from_type_poster_priority(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.TITLE, CrawlerResultFields.POSTER))

    provider = FakeCrawlerProvider(
        {
            Website.FC2: build_image_result(
                Website.FC2,
                poster="https://example.test/fc2-poster.jpg",
                image_download=False,
            ),
            Website.FC2HUB: build_image_result(
                Website.FC2HUB,
                poster="https://example.test/fc2hub-poster.jpg",
                image_download=True,
            ),
        }
    )
    scraper = FileScraper(Fc2PosterPriorityConfig(), provider)
    task_input = CrawlerInput.empty()
    task_input.number = "FC2-1234567"

    result = await scraper._call_crawlers(
        task_input,
        classification=classify_scrape_task(task_input, Config(website_fc2=[Website.FC2, Website.FC2HUB])),
    )

    assert result is not None
    assert result.title == "fc2 title"
    assert result.poster == "https://example.test/fc2hub-poster.jpg"
    assert result.poster_from == Website.FC2HUB.value
    assert result.poster_list == [
        (Website.FC2HUB.value, "https://example.test/fc2hub-poster.jpg", True),
    ]


@pytest.mark.asyncio
async def test_fc2_field_priority_stops_after_complete_fc2cmadb_record(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        ManualConfig,
        "REDUCED_FIELDS",
        (
            CrawlerResultFields.TITLE,
            CrawlerResultFields.OUTLINE,
            CrawlerResultFields.SCORE,
            CrawlerResultFields.RUNTIME,
            CrawlerResultFields.POSTER,
        ),
    )
    records: list[Website] = []
    fc2cmadb = build_image_result(
        Website.FC2PPVDB,
        poster="https://fc2cmadb.test/poster.jpg",
        image_download=True,
    )
    fc2cmadb.runtime = "61"
    fallback = build_image_result(Website.FC2, poster="https://fc2.test/poster.jpg")
    fallback.outline = "fallback outline"
    fallback.score = "4.5"
    provider = ResultRecordingCrawlerProvider(
        {
            Website.FC2PPVDB: ResultRecordingCrawler(Website.FC2PPVDB, records, fc2cmadb),
            Website.FC2: ResultRecordingCrawler(Website.FC2, records, fallback),
        }
    )
    config = Config(scrape_like="info", website_fc2=[Website.FC2PPVDB, Website.FC2])
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "FC2-1234567"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.title == "fc2ppvdb title"
    assert result.runtime == "61"
    assert result.outline == ""
    assert records == [Website.FC2PPVDB]


@pytest.mark.asyncio
async def test_fc2_field_priority_still_falls_back_for_missing_core_fields(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ManualConfig, "REDUCED_FIELDS", (CrawlerResultFields.TITLE, CrawlerResultFields.RUNTIME))
    records: list[Website] = []
    fc2cmadb = build_result(Website.FC2PPVDB)
    fallback = build_result(Website.FC2, runtime="61")
    provider = ResultRecordingCrawlerProvider(
        {
            Website.FC2PPVDB: ResultRecordingCrawler(Website.FC2PPVDB, records, fc2cmadb),
            Website.FC2: ResultRecordingCrawler(Website.FC2, records, fallback),
        }
    )
    config = Config(scrape_like="info", website_fc2=[Website.FC2PPVDB, Website.FC2])
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "FC2-1234567"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.runtime == "61"
    assert records == [Website.FC2PPVDB, Website.FC2]


@pytest.mark.asyncio
async def test_fc2_field_priority_skips_trailer_fallback_when_trailer_download_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        ManualConfig,
        "REDUCED_FIELDS",
        (CrawlerResultFields.TITLE, CrawlerResultFields.TRAILER),
    )
    records: list[Website] = []
    fc2cmadb = build_result(Website.FC2PPVDB)
    fallback = build_result(Website.FC2)
    fallback.trailer = "https://fc2.test/trailer.mp4"
    provider = ResultRecordingCrawlerProvider(
        {
            Website.FC2PPVDB: ResultRecordingCrawler(Website.FC2PPVDB, records, fc2cmadb),
            Website.FC2: ResultRecordingCrawler(Website.FC2, records, fallback),
        }
    )
    config = Config(scrape_like="info", website_fc2=[Website.FC2PPVDB, Website.FC2])
    config.download_files = [item for item in config.download_files if item != DownloadableFile.TRAILER]
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "FC2-1234567"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.title == "fc2ppvdb title"
    assert result.trailer == ""
    assert records == [Website.FC2PPVDB]


@pytest.mark.asyncio
async def test_fc2_field_priority_keeps_trailer_fallback_when_trailer_download_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        ManualConfig,
        "REDUCED_FIELDS",
        (CrawlerResultFields.TITLE, CrawlerResultFields.TRAILER),
    )
    records: list[Website] = []
    fc2cmadb = build_result(Website.FC2PPVDB)
    fallback = build_result(Website.FC2)
    fallback.trailer = "https://fc2.test/trailer.mp4"
    provider = ResultRecordingCrawlerProvider(
        {
            Website.FC2PPVDB: ResultRecordingCrawler(Website.FC2PPVDB, records, fc2cmadb),
            Website.FC2: ResultRecordingCrawler(Website.FC2, records, fallback),
        }
    )
    config = Config(scrape_like="info", website_fc2=[Website.FC2PPVDB, Website.FC2])
    assert DownloadableFile.TRAILER in config.download_files
    scraper = FileScraper(config, provider)
    task_input = CrawlTask.empty()
    task_input.number = "FC2-1234567"

    result = await scraper.run(task_input, FileMode.Default)

    assert result is not None
    assert result.trailer == "https://fc2.test/trailer.mp4"
    assert records == [Website.FC2PPVDB, Website.FC2]
