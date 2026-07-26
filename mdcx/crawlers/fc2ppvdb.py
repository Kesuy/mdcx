#!/usr/bin/env python3
import html
import json
from http.cookies import SimpleCookie
from typing import Any, override

from bs4 import BeautifulSoup

from ..config.manager import manager
from ..config.models import Website
from .base import BaseCrawler, Context, CralwerException, CrawlerData


def get_title(data):  # 获取标题
    return data.get("article", {}).get("title", "")


def get_cover(data):  # 获取封面URL
    image_url = data.get("article", {}).get("image_url", "")
    if image_url and "no-image" not in image_url:
        return image_url
    return ""


def get_release_date(data):  # 获取发行日期
    return data.get("article", {}).get("release_date", "")


def get_actors(data):  # 获取演员
    actresses = data.get("article", {}).get("actresses", [])
    return [actress.get("name", "") for actress in actresses if actress.get("name")] if actresses else []


def get_tags(data):  # 获取标签
    tags = data.get("article", {}).get("tags", [])
    return [tag.get("name", "") for tag in tags if tag.get("name")] if tags else []


def get_studio(data):  # 获取厂家
    writer = data.get("article", {}).get("writer", {})
    return writer.get("name", "")


def get_video_type(data):  # 获取视频类型
    censored = data.get("article", {}).get("censored")
    if censored == "無":
        return "無碼"
    if censored == "有":
        return "有碼"
    tag_names = set(get_tags(data))
    if "無修正" in tag_names:
        return "無碼"
    return ""


def get_video_url(data):  # 获取视频URL
    # video_id = data.get("article", {}).get("video_id")
    # if video_id:
    #     return f"https://example.com/videos/{video_id}.mp4"
    return ""


def get_video_time(data):  # 获取视频时长
    duration = str(data.get("article", {}).get("duration", "")).strip()
    if not duration:
        return ""

    temp_list = duration.split(":")
    if len(temp_list) == 3:
        hours, minutes, seconds = temp_list
        try:
            total_minutes = int(hours) * 60 + int(minutes)
            if total_minutes == 0 and int(seconds) > 0:
                return "1"
            return str(total_minutes)
        except ValueError:
            return duration
    if len(temp_list) <= 2 and temp_list[0].isdigit():
        return str(int(temp_list[0]))
    return duration


def cookie_str_to_dict(cookie_str: str) -> dict:  # cookie 转为字典
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_str)
    except Exception:
        return {}
    return {key: morsel.value for key, morsel in cookie.items()}


def has_fc2cmadb_session(cookie_str: str) -> bool:
    return bool(cookie_str_to_dict(cookie_str).get("fc2cmadb-session"))


def normalize_fc2_number(number: str) -> str:
    return number.upper().replace("FC2PPV", "").replace("FC2-PPV-", "").replace("FC2-", "").replace("-", "").strip()


def parse_article_page(page_html: str) -> dict[str, Any]:
    soup = BeautifulSoup(page_html, "html.parser")
    page_script = soup.select_one('script[type="application/json"][data-page]')
    if page_script is None:
        raise ValueError("详情页缺少 Inertia 页面数据")

    raw_page = page_script.string or page_script.get_text()
    page_data = json.loads(html.unescape(raw_page))
    if page_data.get("component") != "Articles/Show":
        raise ValueError(f"详情页组件异常: {page_data.get('component') or '未知'}")

    article = page_data.get("props", {}).get("article")
    if not isinstance(article, dict):
        raise ValueError("详情页未返回影片数据")
    return {"article": article}


def get_response_final_url(response) -> str:
    headers = getattr(response, "headers", {}) or {}
    return str(headers.get("x-mdcx-final-url") or getattr(response, "url", "") or "")


async def fetch_article_info(
    async_client,
    *,
    base_url: str,
    number: str,
    cookies: dict[str, str],
    use_proxy: bool,
) -> tuple[dict[str, Any] | None, str]:
    article_url = f"{base_url}/articles/{number}"
    response, error = await async_client.request(
        "GET",
        article_url,
        cookies=cookies,
        use_proxy=use_proxy,
    )
    if response is None:
        return None, f"详情页请求失败: {error}"
    if response.status_code != 200:
        return None, f"详情页请求失败: HTTP {response.status_code}"
    final_url = get_response_final_url(response)
    if "/login" in final_url:
        return None, f"详情页跳转到登录页，fc2cmadb Cookie 未生效: {final_url}"

    page_html = str(getattr(response, "text", "") or "")
    try:
        return parse_article_page(page_html), ""
    except Exception as e:
        if "ログイン" in page_html or "login" in page_html.lower():
            return None, f"详情页返回登录页面，fc2cmadb Cookie 可能无效或已过期: {e}"
        return None, f"详情页数据解析失败: {e}"


class Fc2ppvdbCrawler(BaseCrawler):
    @classmethod
    @override
    def site(cls) -> Website:
        return Website.FC2PPVDB

    @classmethod
    @override
    def base_url_(cls) -> str:
        return "https://fc2cmadb.com"

    @override
    async def _run(self, ctx: Context):
        number = normalize_fc2_number(ctx.input.number)
        article_url = f"{self.base_url}/articles/{number}"
        ctx.debug(f"番号地址: {article_url}")
        ctx.debug_info.detail_urls = [article_url]

        cookies = cookie_str_to_dict(manager.config.fc2ppvdb)
        use_proxy = manager.config.use_proxy
        html_info, error = await fetch_article_info(
            self.async_client,
            base_url=self.base_url,
            number=number,
            cookies=cookies,
            use_proxy=use_proxy,
        )
        if html_info is None:
            raise CralwerException(error)

        title = get_title(html_info)
        if not title:
            raise CralwerException("数据获取失败: 未获取到title！")
        cover_url = get_cover(html_info)
        if "http" not in cover_url:
            ctx.debug("数据获取失败: 未获取到cover！")
        release_date = get_release_date(html_info)
        actors = get_actors(html_info)
        tags = [tag for tag in get_tags(html_info) if tag != "無修正"]
        studio = get_studio(html_info)  # 使用卖家作为厂商
        if "fc2_seller" in manager.config.fields_rule and studio:
            actors = [studio]
        video_type = get_video_type(html_info)

        data = CrawlerData(
            number="FC2-" + str(number),
            title=title,
            originaltitle=title,
            outline="",
            actors=actors,
            originalplot="",
            tags=tags,
            release=release_date,
            year=release_date[:4] if release_date else "",
            runtime=get_video_time(html_info),
            score="",
            series="FC2系列",
            directors=[],
            studio=studio,
            publisher=studio,
            thumb=cover_url,
            poster=cover_url,
            extrafanart=[],
            trailer=get_video_url(html_info),
            image_download=False,
            mosaic="无码" if video_type == "無碼" else "有码" if video_type == "有碼" else "",
            external_id=article_url,
            wanted="",
        )
        result = data.to_result()
        result.source = self.site().value
        ctx.debug("数据获取成功！")
        return result

    @override
    async def _generate_search_url(self, ctx: Context) -> list[str] | str | None:
        return None

    @override
    async def _parse_search_page(self, ctx: Context, html, search_url: str) -> list[str] | str | None:
        return None

    @override
    async def _parse_detail_page(self, ctx: Context, html, detail_url: str) -> CrawlerData | None:
        return None
