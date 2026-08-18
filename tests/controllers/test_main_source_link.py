from mdcx.config.enums import Website
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.types import CrawlersResult


def test_source_page_url_prefers_number_field_source():
    data = CrawlersResult.empty()
    data.field_sources[CrawlerResultFields.NUMBER] = Website.FC2.value
    data.field_sources[CrawlerResultFields.TITLE] = Website.JAVDB.value
    data.external_ids = {
        Website.JAVDB: "https://javdb.example/v/abc",
        Website.FC2: "https://adult.contents.fc2.com/article/4956715/",
    }

    assert MyMAinWindow._source_page_url(data) == "https://adult.contents.fc2.com/article/4956715/"


def test_source_page_url_falls_back_to_another_valid_detail_url():
    data = CrawlersResult.empty()
    data.field_sources[CrawlerResultFields.NUMBER] = Website.JAVDB.value
    data.external_ids = {
        Website.JAVDB: "abc123",
        Website.FC2: "https://adult.contents.fc2.com/article/4956715/",
    }

    assert MyMAinWindow._source_page_url(data) == "https://adult.contents.fc2.com/article/4956715/"


def test_source_page_url_rejects_non_web_external_ids():
    data = CrawlersResult.empty()
    data.external_ids = {Website.JAVDB: "abc123", Website.MISSAV: "dm42"}

    assert MyMAinWindow._source_page_url(data) == ""
