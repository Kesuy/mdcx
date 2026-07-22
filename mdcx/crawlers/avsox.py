#!/usr/bin/env python3
import json
import re
from dataclasses import dataclass
from typing import Any, override
from urllib.parse import quote, urlsplit

from lxml import etree
from parsel import Selector

from ..base.web import get_avsox_domain
from ..config.models import Website
from ..models.types import CrawlerInput
from .base import Context, CralwerException, CrawlerData, GenericBaseCrawler


def normalize_avsox_number(number: str) -> str:
    """将 AVSOX 番号规范化为可稳定比较的形式。"""
    return re.sub(r"[\s\u200b\ufeff]+", "", number).upper().replace("-PPV", "")


def extract_csrf_token(html: str) -> str:
    match = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)', html, re.I)
    return match.group(1) if match else ""


def extract_movie_id(detail_url: str) -> str:
    path = urlsplit(detail_url).path
    match = re.search(r"/(?:movies|movie)/([^/?#]+)", path, re.I)
    return match.group(1) if match else ""


def select_search_movie(movies: list[dict[str, Any]], number: str) -> dict[str, Any] | None:
    """从新版 AVSOX 搜索 API 结果中选择完全匹配的番号。"""
    expected = normalize_avsox_number(number)
    for movie in movies:
        if normalize_avsox_number(str(movie.get("movieFanHao") or "")) == expected:
            return movie
    return None


def _entity_name(entity: Any, key: str) -> str:
    if not isinstance(entity, dict):
        return ""
    return str(entity.get(key) or entity.get(f"{key}_cn") or entity.get(f"{key}_ja") or "").strip()


def movie_to_crawler_data(movie: dict[str, Any], *, requested_number: str, detail_url: str) -> CrawlerData:
    """将新版 AVSOX getMovie API 的 data 对象转换为 MDCx 数据。"""
    title = str(
        movie.get("title")
        or movie.get("title_cn")
        or movie.get("title_tw")
        or movie.get("title_en")
        or movie.get("title_ja")
        or ""
    ).strip()
    original_title = str(movie.get("title_ja") or title).strip()
    description = str(
        movie.get("description")
        or movie.get("description_cn")
        or movie.get("description_tw")
        or movie.get("description_en")
        or movie.get("description_ja")
        or ""
    ).strip()
    actors = [name for item in movie.get("star") or [] if (name := _entity_name(item, "starName"))]
    tags = [name for item in movie.get("genre") or [] if (name := _entity_name(item, "genreName"))]
    directors = [
        name
        for item in (
            [movie.get("director")] if isinstance(movie.get("director"), dict) else movie.get("director") or []
        )
        if (name := _entity_name(item, "directorName"))
    ]
    studio = _entity_name(movie.get("studio"), "studioName")
    label = _entity_name(movie.get("label"), "labelName")
    series = _entity_name(movie.get("series"), "seriesName")
    release = str(movie.get("releaseDate") or "").strip()
    runtime_value = movie.get("length")
    runtime = str(runtime_value) if runtime_value not in (None, "") else ""
    poster = str(movie.get("posterSmall") or "").strip()
    thumb = str(movie.get("posterLarge") or poster).strip()
    extrafanart = [str(url).strip() for url in movie.get("sampleLarge") or [] if str(url).strip()]

    return CrawlerData(
        number=requested_number or str(movie.get("movieFanHao") or "").strip(),
        title=title,
        originaltitle=original_title,
        outline=description,
        originalplot=description,
        actors=actors,
        all_actors=actors,
        directors=directors,
        tags=tags,
        release=release,
        year=release[:4] if release else "",
        runtime=runtime,
        series=series,
        studio=studio,
        publisher=label or studio,
        thumb=thumb,
        poster=poster,
        extrafanart=extrafanart,
        trailer="",
        image_download=bool(thumb or poster),
        mosaic="无码",
        external_id=detail_url,
    )


def get_actor(html):
    result = ",".join(html.xpath("//div[@id='avatar-waterfall']/a/span/text()"))
    return result


def get_web_number(html):
    result = html.xpath('//div[@class="col-md-3 info"]/p/span[@style="color:#CC0000;"]/text()')
    return result[0] if result else ""


def get_title(html):
    result = html.xpath('//div[@class="container"]/h3/text()')
    return result[0] if result else ""


def get_cover(html):
    result = html.xpath('//a[@class="bigImage"]/@href')
    return result[0] if result else ""


def get_poster(html, count):
    poster_url = html.xpath("//div[@id='waterfall']/div[" + str(count) + "]/a/div[@class='photo-frame']/img/@src")[0]
    return poster_url


def get_tag(html):
    result = html.xpath('//span[@class="genre"]/a/text()')
    return ",".join(result)


def get_release(html):
    result = html.xpath(
        '//span[contains(text(),"发行时间:") or contains(text(),"發行日期:") or contains(text(),"発売日:")]/../text()'
    )
    return result[0].strip() if result else ""


def get_year(release):
    return release[:4] if release else release


def get_runtime(html):
    result = html.xpath(
        '//span[contains(text(),"长度:") or contains(text(),"長度:") or contains(text(),"収録時間:")]/../text()'
    )
    return re.findall(r"(\d+)", result[0])[0] if result else ""


def get_series(html):
    result = html.xpath('//p/a[contains(@href,"/series/")]/text()')
    return result[0].strip() if result else ""


def get_studio(html):
    result = html.xpath('//p/a[contains(@href,"/studio/")]/text()')
    return result[0].strip() if result else ""


def get_real_url(number, html):
    page_url = ""
    url_list = html.xpath('//*[@id="waterfall"]/div/a/@href')
    i = 0
    if url_list:
        for i in range(1, len(url_list) + 1):
            number_get = str(
                html.xpath('//*[@id="waterfall"]/div[' + str(i) + ']/a/div[@class="photo-info"]/span/date[1]/text()')
            ).strip(" ['']")
            if number.upper().replace("-PPV", "") == number_get.upper().replace("-PPV", ""):
                page_url = "https:" + url_list[i - 1]
                break
    return page_url, i


@dataclass
class AvsoxContext(Context):
    search_poster: str = ""


class AvsoxCrawler(GenericBaseCrawler[AvsoxContext]):
    @classmethod
    @override
    def site(cls) -> Website:
        return Website.AVSOX

    @classmethod
    @override
    def base_url_(cls) -> str:
        return ""

    @override
    def new_context(self, input: CrawlerInput) -> AvsoxContext:
        return AvsoxContext(input=input)

    async def _load_spa_token(self, url: str) -> str:
        html, error = await self.async_client.get_text(url)
        if html is None:
            raise CralwerException(f"AVSOX 页面请求失败: {error}")
        token = extract_csrf_token(html)
        if not token:
            raise CralwerException("AVSOX 页面缺少 CSRF token")
        return token

    async def _api_request(
        self,
        *,
        base_url: str,
        method: str,
        args: list[Any],
        token: str,
        referer: str,
    ) -> Any:
        response, error = await self.async_client.request(
            "POST",
            f"{base_url}/javu/data/api/{method}",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": base_url,
                "Referer": referer,
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": token,
            },
            data=json.dumps(args, ensure_ascii=False, separators=(",", ":")),
        )
        if response is None:
            raise CralwerException(f"AVSOX API {method} 请求失败: {error}")
        try:
            payload = response.json()
        except Exception as exc:
            raise CralwerException(f"AVSOX API {method} 返回非 JSON 数据") from exc
        if not isinstance(payload, dict) or payload.get("code") != 200:
            message = payload.get("message") if isinstance(payload, dict) else "返回结构异常"
            raise CralwerException(f"AVSOX API {method} 失败: {message}")
        return payload.get("data")

    @override
    async def _run(self, ctx: AvsoxContext):
        requested_number = ctx.input.number.strip()
        if ctx.input.appoint_url:
            detail_url = ctx.input.appoint_url.strip()
            parsed = urlsplit(detail_url)
            if not parsed.scheme or not parsed.netloc:
                raise CralwerException("指定的 AVSOX 详情页 URL 无效")
            base_url = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            movie_id = extract_movie_id(detail_url)
            if not movie_id:
                raise CralwerException("指定 URL 中未找到 AVSOX 影片 ID")
            token = await self._load_spa_token(detail_url)
        else:
            if not requested_number:
                raise CralwerException("番号为空")
            base_url = (self.base_url or await get_avsox_domain()).rstrip("/")
            search_url = f"{base_url}/cn/search/{quote(requested_number)}"
            ctx.debug_info.search_urls = [search_url]
            ctx.debug(f"搜索页 URL: {search_url}")
            token = await self._load_spa_token(search_url)
            movies = await self._api_request(
                base_url=base_url,
                method="search",
                args=[{"search": requested_number, "lang": "cn"}, 60, 1],
                token=token,
                referer=search_url,
            )
            if not isinstance(movies, list):
                raise CralwerException("AVSOX 搜索 API 返回结构异常")
            movie = select_search_movie(movies, requested_number)
            if movie is None:
                raise CralwerException("搜索结果: 未匹配到番号")
            movie_id = str(movie.get("movieId") or "").strip()
            if not movie_id:
                raise CralwerException("AVSOX 搜索结果缺少影片 ID")
            detail_url = f"{base_url}/cn/movies/{movie_id}"

        ctx.debug_info.detail_urls = [detail_url]
        ctx.debug(f"详情页 URL: {detail_url}")
        movie = await self._api_request(
            base_url=base_url,
            method="getMovie",
            args=[movie_id, "cn"],
            token=token,
            referer=detail_url,
        )
        if not isinstance(movie, dict):
            raise CralwerException("AVSOX 详情 API 返回结构异常")
        data = movie_to_crawler_data(
            movie,
            requested_number=requested_number or str(movie.get("movieFanHao") or "").strip(),
            detail_url=detail_url,
        )
        if not data.title:
            raise CralwerException("数据获取失败: 未获取到 title")
        data.source = self.site().value
        return await self.post_process(ctx, data.to_result())

    @override
    async def _generate_search_url(self, ctx: AvsoxContext) -> list[str] | str | None:
        avsox_url = await get_avsox_domain()
        return f"{avsox_url}/cn/search/{ctx.input.number}"

    @override
    async def _parse_search_page(self, ctx: AvsoxContext, html: Selector, search_url: str) -> list[str] | str | None:
        html_search = etree.fromstring(html.get(), etree.HTMLParser())
        detail_url, count = get_real_url(ctx.input.number, html_search)
        if not detail_url:
            raise CralwerException("搜索结果: 未匹配到番号")
        ctx.search_poster = get_poster(html_search, count)
        return [detail_url]

    @override
    async def _parse_detail_page(self, ctx: AvsoxContext, html: Selector, detail_url: str) -> CrawlerData | None:
        detail_page = etree.fromstring(html.get(), etree.HTMLParser())
        web_number = get_web_number(detail_page)
        title = get_title(detail_page).replace(web_number + " ", "").strip()
        if not title:
            raise CralwerException("数据获取失败: 未获取到title")

        actor = get_actor(detail_page)
        release = get_release(detail_page)
        studio = get_studio(detail_page)
        actors = [item.strip() for item in actor.split(",") if item.strip()]
        tags = [item.strip() for item in get_tag(detail_page).split(",") if item.strip()]
        return CrawlerData(
            number=ctx.input.number,
            title=title,
            originaltitle=title,
            actors=actors,
            all_actors=actors,
            tags=tags,
            release=release,
            year=get_year(release),
            runtime=get_runtime(detail_page),
            series=get_series(detail_page),
            studio=studio,
            publisher=studio,
            thumb=get_cover(detail_page),
            poster=ctx.search_poster,
            extrafanart=[],
            trailer="",
            image_download=bool(ctx.search_poster),
            mosaic="无码",
            external_id=detail_url,
        )
