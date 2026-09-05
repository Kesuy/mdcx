from mdcx.config.enums import FixedScrapingType, Website
from mdcx.config.models import FieldConfig, FieldPriorityConfig
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.types import CrawlerDebugInfo, CrawlerInput, CrawlerResponse, CrawlerResult


class FakeCrawler:
    def __init__(self, data: CrawlerResult | None, error: Exception | None = None):
        self._data = data
        self._error = error

    async def run(self, task_input: CrawlerInput) -> CrawlerResponse:
        return CrawlerResponse(
            debug_info=CrawlerDebugInfo(execution_time=0.01, error=self._error),
            data=self._data,
        )


class FakeCrawlerProvider:
    def __init__(self, website_data: dict[Website, CrawlerResult | tuple[CrawlerResult | None, Exception | None]]):
        self._website_crawlers = {}
        for site, data in website_data.items():
            if isinstance(data, tuple):
                self._website_crawlers[site] = FakeCrawler(data[0], data[1])
            else:
                self._website_crawlers[site] = FakeCrawler(data)

    async def get(self, site: Website):
        return self._website_crawlers[site]


class RecordingCrawler:
    def __init__(self, site: Website, records: list[tuple[str, str]], should_raise: bool = False):
        self._site = site
        self._records = records
        self._should_raise = should_raise

    async def run(self, task_input: CrawlerInput) -> CrawlerResponse:
        self._records.append((self._site.value, task_input.number))
        if self._should_raise:
            raise RuntimeError("boom")

        data = CrawlerResult.empty()
        data.title = "ok"
        data.source = self._site.value
        data.external_id = f"{self._site.value}:id"
        return CrawlerResponse(
            debug_info=CrawlerDebugInfo(execution_time=0.01),
            data=data,
        )


class RecordingCrawlerProvider:
    def __init__(self, crawlers: dict[Website, RecordingCrawler]):
        self._website_crawlers = crawlers

    async def get(self, site: Website):
        return self._website_crawlers[site]


class ResultRecordingCrawler:
    def __init__(
        self,
        site: Website,
        records: list[Website],
        data: CrawlerResult | None,
        error: Exception | None = None,
    ):
        self._site = site
        self._records = records
        self._data = data
        self._error = error

    async def run(self, task_input: CrawlerInput) -> CrawlerResponse:
        self._records.append(self._site)
        return CrawlerResponse(
            debug_info=CrawlerDebugInfo(execution_time=0.01, error=self._error),
            data=self._data,
        )


class ResultRecordingCrawlerProvider:
    def __init__(self, crawlers: dict[Website, ResultRecordingCrawler]):
        self._website_crawlers = crawlers

    async def get(self, site: Website):
        return self._website_crawlers[site]


class FakeConfig:
    def get_field_config(self, field: CrawlerResultFields) -> FieldConfig:
        if field in (CrawlerResultFields.RUNTIME, CrawlerResultFields.RELEASE, CrawlerResultFields.YEAR):
            return FieldConfig(site_prority=[Website.AVBASE, Website.JAVDB])
        return FieldConfig(site_prority=[])


class TypePriorityConfig(FakeConfig):
    def get_type_field_config(
        self, scraping_type: FixedScrapingType, field: CrawlerResultFields
    ) -> FieldPriorityConfig:
        if scraping_type == FixedScrapingType.YOUMA and field == CrawlerResultFields.RUNTIME:
            return FieldPriorityConfig(site_prority=[Website.JAVDB, Website.AVBASE])
        return FieldPriorityConfig()


class ImagePriorityConfig(FakeConfig):
    scrape_like = "info"
    field_priority_try_all_images = True

    def get_field_config(self, field: CrawlerResultFields) -> FieldConfig:
        if field in (CrawlerResultFields.POSTER, CrawlerResultFields.THUMB):
            return FieldConfig(site_prority=[Website.AVBASE, Website.JAVDB])
        return FieldConfig(site_prority=[])

    def get_type_field_config(
        self, scraping_type: FixedScrapingType, field: CrawlerResultFields
    ) -> FieldPriorityConfig:
        if field in (CrawlerResultFields.POSTER, CrawlerResultFields.THUMB):
            return FieldPriorityConfig(site_prority=[Website.AVBASE, Website.JAVDB])
        return FieldPriorityConfig()


class Fc2PosterPriorityConfig(FakeConfig):
    scrape_like = "info"
    field_priority_try_all_images = True

    def get_field_config(self, field: CrawlerResultFields) -> FieldConfig:
        if field == CrawlerResultFields.TITLE:
            return FieldConfig(site_prority=[Website.FC2, Website.FC2HUB])
        if field == CrawlerResultFields.POSTER:
            return FieldConfig(site_prority=[Website.FC2HUB])
        if field == CrawlerResultFields.THUMB:
            return FieldConfig(site_prority=[Website.FC2HUB, Website.FC2])
        return FieldConfig(site_prority=[])

    def get_type_field_config(
        self, scraping_type: FixedScrapingType, field: CrawlerResultFields
    ) -> FieldPriorityConfig:
        if scraping_type == FixedScrapingType.FC2 and field == CrawlerResultFields.TITLE:
            return FieldPriorityConfig(site_prority=[Website.FC2, Website.FC2HUB])
        if scraping_type == FixedScrapingType.FC2 and field == CrawlerResultFields.POSTER:
            return FieldPriorityConfig(site_prority=[Website.FC2HUB])
        if scraping_type == FixedScrapingType.FC2 and field == CrawlerResultFields.THUMB:
            return FieldPriorityConfig(site_prority=[Website.FC2HUB, Website.FC2])
        return FieldPriorityConfig()


class ClassificationConfig:
    fixed_scraping_type = FixedScrapingType.AUTO
    website_youma = {Website.DMM}
    website_wuma = {Website.JAVBUS}
    website_suren = {Website.MGSTAGE}
    website_fc2 = {Website.FC2}
    website_oumei = {Website.THEPORNDB}
    website_guochan = {Website.MDTV}


def build_result(site: Website, runtime: str = "", release: str = "", year: str = "") -> CrawlerResult:
    result = CrawlerResult.empty()
    result.source = site.value
    result.external_id = f"{site.value}:id"
    result.title = f"{site.value} title"
    result.runtime = runtime
    result.release = release
    result.year = year
    return result


def build_image_result(site: Website, poster: str = "", thumb: str = "", image_download: bool = True) -> CrawlerResult:
    result = build_result(site)
    result.poster = poster
    result.thumb = thumb
    result.image_download = image_download
    return result
