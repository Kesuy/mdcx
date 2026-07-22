import json
from types import SimpleNamespace

import pytest

from mdcx.crawlers.avsox import AvsoxCrawler, movie_to_crawler_data, select_search_movie
from mdcx.models.types import CrawlerInput


@pytest.fixture
def h4610_movie() -> dict:
    return {
        "movieId": "nrzebvn",
        "movieFanHao": "H4610-ori696",
        "title": "望月 奈々",
        "title_ja": "望月 奈々",
        "releaseDate": "2010-04-24",
        "length": 48,
        "posterSmall": "https://file.netcdn.space/storage/h4610/moviepages/ori696/images/thumb_s.jpg",
        "posterLarge": "https://file.netcdn.space/storage/h4610/moviepages/ori696/images/movie.jpg",
        "sampleLarge": ["https://example.test/sample-1.jpg"],
        "description_ja": "作品简介",
        "studio": {"studioName": "エッチな4610"},
        "genre": [
            {"genreName": "辣妹"},
            {"genreName": "素人"},
            {"genreName": "内射"},
        ],
        "star": [
            {"starName": "望月奈々"},
        ],
    }


def test_select_search_movie_matches_case_insensitively():
    movies = [
        {"movieId": "wrong", "movieFanHao": "H4610-ori641"},
        {"movieId": "nrzebvn", "movieFanHao": "H4610-ori696"},
    ]

    assert select_search_movie(movies, "H4610-ORI696")["movieId"] == "nrzebvn"


def test_movie_to_crawler_data_maps_new_avsox_api_fields(h4610_movie: dict):
    data = movie_to_crawler_data(
        h4610_movie,
        requested_number="H4610-ORI696",
        detail_url="https://avsox.click/cn/movies/nrzebvn",
    )

    assert data.number == "H4610-ORI696"
    assert data.title == "望月 奈々"
    assert data.originaltitle == "望月 奈々"
    assert data.actors == ["望月奈々"]
    assert data.all_actors == ["望月奈々"]
    assert data.tags == ["辣妹", "素人", "内射"]
    assert data.release == "2010-04-24"
    assert data.year == "2010"
    assert data.runtime == "48"
    assert data.studio == "エッチな4610"
    assert data.publisher == "エッチな4610"
    assert data.thumb.endswith("/movie.jpg")
    assert data.poster.endswith("/thumb_s.jpg")
    assert data.extrafanart == ["https://example.test/sample-1.jpg"]
    assert data.outline == "作品简介"
    assert data.originalplot == "作品简介"
    assert data.image_download is True
    assert data.mosaic == "无码"
    assert data.external_id == "https://avsox.click/cn/movies/nrzebvn"


class FakeAvsoxClient:
    def __init__(self, movie: dict):
        self.movie = movie
        self.calls: list[tuple[str, str, object]] = []

    async def get_text(self, url: str, **kwargs):
        self.calls.append(("GET", url, None))
        return '<meta name="csrf-token" content="test-csrf">', ""

    async def request(self, method: str, url: str, **kwargs):
        payload = json.loads(kwargs["data"])
        self.calls.append((method, url, payload))
        if url.endswith("/search"):
            data = [self.movie]
        elif url.endswith("/getMovie"):
            data = self.movie
        else:
            raise AssertionError(f"unexpected API URL: {url}")
        return SimpleNamespace(json=lambda: {"code": 200, "data": data}), ""


@pytest.mark.asyncio
async def test_avsox_crawler_uses_spa_api_for_search_and_detail(h4610_movie: dict):
    client = FakeAvsoxClient(h4610_movie)
    crawler = AvsoxCrawler(client=client, base_url="https://avsox.click")
    crawler_input = CrawlerInput.empty()
    crawler_input.number = "H4610-ORI696"

    response = await crawler.run(crawler_input)

    assert response.data is not None
    assert response.data.title == "望月 奈々"
    assert response.data.external_id == "https://avsox.click/cn/movies/nrzebvn"
    assert client.calls == [
        ("GET", "https://avsox.click/cn/search/H4610-ORI696", None),
        (
            "POST",
            "https://avsox.click/javu/data/api/search",
            [{"search": "H4610-ORI696", "lang": "cn"}, 60, 1],
        ),
        (
            "POST",
            "https://avsox.click/javu/data/api/getMovie",
            ["nrzebvn", "cn"],
        ),
    ]


@pytest.mark.asyncio
async def test_avsox_crawler_normalizes_language_path_in_configured_url(h4610_movie: dict):
    client = FakeAvsoxClient(h4610_movie)
    crawler = AvsoxCrawler(client=client, base_url="https://avsox.click/cn")
    crawler_input = CrawlerInput.empty()
    crawler_input.number = "H0930-GOL122"
    client.movie = {**h4610_movie, "movieId": "example-id", "movieFanHao": "H0930-gol122"}

    response = await crawler.run(crawler_input)

    assert response.data is not None
    assert client.calls == [
        ("GET", "https://avsox.click/cn/search/H0930-GOL122", None),
        (
            "POST",
            "https://avsox.click/javu/data/api/search",
            [{"search": "H0930-GOL122", "lang": "cn"}, 60, 1],
        ),
        (
            "POST",
            "https://avsox.click/javu/data/api/getMovie",
            ["example-id", "cn"],
        ),
    ]


@pytest.mark.asyncio
async def test_avsox_crawler_supports_appointed_spa_detail_url(h4610_movie: dict):
    client = FakeAvsoxClient(h4610_movie)
    crawler = AvsoxCrawler(client=client)
    crawler_input = CrawlerInput.empty()
    crawler_input.appoint_url = "https://avsox.click/cn/movies/nrzebvn"

    response = await crawler.run(crawler_input)

    assert response.data is not None
    assert response.data.number == "H4610-ori696"
    assert response.data.title == "望月 奈々"
    assert response.data.external_id == crawler_input.appoint_url
    assert client.calls == [
        ("GET", "https://avsox.click/cn/movies/nrzebvn", None),
        (
            "POST",
            "https://avsox.click/javu/data/api/getMovie",
            ["nrzebvn", "cn"],
        ),
    ]
