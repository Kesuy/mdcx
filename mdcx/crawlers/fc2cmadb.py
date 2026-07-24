#!/usr/bin/env python3
"""fc2cmadb 刮削器

网站: https://fc2cmadb.com
需要登录才能访问详情页，使用 Cookie 鉴权。
支持 Cloudflare bypass (FlareSolverr)。
"""

from typing import override

from ..config.manager import manager
from ..config.models import Website
from .base import BaseCrawler, Context, CralwerException, CrawlerData


def normalize_fc2_number(number: str) -> str:
    """规范化 FC2 番号，去除前缀和分隔符。"""
    return (
        number.upper()
        .replace("FC2PPV", "")
        .replace("FC2-PPV-", "")
        .replace("FC2-", "")
        .replace("-", "")
        .strip()
    )


def parse_cookie(cookie_str: str) -> dict[str, str]:
    """将浏览器 Cookie 字符串解析为 dict。"""
    from http.cookies import SimpleCookie

    cookie = SimpleCookie()
    try:
        cookie.load(cookie_str)
    except Exception:
        return {}
    return {key: morsel.value for key, morsel in cookie.items()}


def get_xhr_headers(article_url: str) -> dict[str, str]:
    """构建 XHR 请求头。"""
    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": article_url,
        "X-Requested-With": "XMLHttpRequest",
    }


def extract_title(data: dict) -> str:
    return data.get("article", {}).get("title", "")


def extract_cover(data: dict) -> str:
    image_url = data.get("article", {}).get("image_url", "")
    if image_url and "no-image" not in image_url:
        return image_url
    return ""


def extract_release_date(data: dict) -> str:
    return data.get("article", {}).get("release_date", "")


def extract_actors(data: dict) -> list[str]:
    actresses = data.get("article", {}).get("actresses", [])
    return [a.get("name", "") for a in actresses if a.get("name")] if actresses else []


def extract_tags(data: dict) -> list[str]:
    tags = data.get("article", {}).get("tags", [])
    return [t.get("name", "") for t in tags if t.get("name")] if tags else []


def extract_studio(data: dict) -> str:
    writer = data.get("article", {}).get("writer", {})
    return writer.get("name", "")


def extract_video_type(data: dict) -> str:
    censored = data.get("article", {}).get("censored")
    if censored == "無":
        return "無碼"
    elif censored == "有":
        return "有碼"
    return ""


def extract_runtime(data: dict) -> str:
    duration = str(data.get("article", {}).get("duration", "")).strip()
    if not duration:
        return ""
    parts = duration.split(":")
    if len(parts) == 3:
        try:
            total_minutes = int(parts[0]) * 60 + int(parts[1])
            if total_minutes == 0 and int(parts[2]) > 0:
                return "1"
            return str(total_minutes)
        except ValueError:
            return duration
    if len(parts) <= 2 and parts[0].isdigit():
        return str(int(parts[0]))
    return duration


class Fc2cmadbCrawler(BaseCrawler):
    @classmethod
    @override
    def site(cls) -> Website:
        return Website.FC2CMADB

    @classmethod
    @override
    def base_url_(cls) -> str:
        return "https://fc2cmadb.com"

    @override
    async def _run(self, ctx: Context):
        number = normalize_fc2_number(ctx.input.number)
        article_url = f"{self.base_url}/articles/{number}"
        xhr_url = f"{self.base_url}/articles/article-info?videoid={number}"

        ctx.debug(f"番号地址: {article_url}")
        ctx.debug_info.detail_urls = [article_url]

        # 解析 Cookie
        cookie_str = manager.config.fc2cmadb
        cookies = parse_cookie(cookie_str) if cookie_str else {}
        use_proxy = manager.config.use_proxy

        # 先访问详情页（warmup，触发 Cloudflare challenge）
        resp_article, err = await self.async_client.request(
            "GET",
            article_url,
            cookies=cookies,
            use_proxy=use_proxy,
        )
        if resp_article is None:
            raise CralwerException(f"详情页请求失败: {err}")
        if resp_article.status_code != 200:
            raise CralwerException(f"详情页请求失败: HTTP {resp_article.status_code}")

        # 检查是否跳转到登录页
        final_url = str(resp_article.headers.get("x-mdcx-final-url") or resp_article.url or "")
        if "/login" in final_url:
            raise CralwerException(f"详情页跳转到登录页，fc2cmadb Cookie 未生效: {final_url}")

        # 请求 XHR API 获取 JSON 数据
        ctx.debug(f"XHR 地址: {xhr_url}")
        resp_xhr, err = await self.async_client.request(
            "GET",
            xhr_url,
            headers=get_xhr_headers(article_url),
            cookies=cookies,
            use_proxy=use_proxy,
        )
        if resp_xhr is None:
            raise CralwerException(f"XHR 请求失败: {err}")

        try:
            data = resp_xhr.json()
        except Exception as e:
            content_type = resp_xhr.headers.get("content-type", "")
            text = (resp_xhr.text or "").strip()
            if "ログイン" in text or "login" in text.lower():
                raise CralwerException("XHR 返回登录页，fc2cmadb Cookie 可能无效或已过期")
            if text.lstrip().startswith("<!DOCTYPE html"):
                raise CralwerException("XHR 返回 HTML 页面而不是 JSON，可能需要 Cloudflare bypass")
            raise CralwerException(f"XHR JSON 解析失败: {e}，响应: {text[:200]}")

        if not isinstance(data, dict):
            raise CralwerException(f"XHR 返回数据结构异常: {type(data).__name__}")

        # 解析字段
        title = extract_title(data)
        if not title:
            raise CralwerException("数据获取失败: 未获取到 title！")

        cover_url = extract_cover(data)
        if "http" not in cover_url:
            ctx.debug("数据获取警告: 未获取到 cover！")

        release_date = extract_release_date(data)
        actors = extract_actors(data)
        tags = [t for t in extract_tags(data) if t != "無修正"]
        studio = extract_studio(data)
        if "fc2_seller" in manager.config.fields_rule and studio:
            actors = [studio]
        video_type = extract_video_type(data)

        result_data = CrawlerData(
            number="FC2-" + str(number),
            title=title,
            originaltitle=title,
            outline="",
            actors=actors,
            originalplot="",
            tags=tags,
            release=release_date,
            year=release_date[:4] if release_date else "",
            runtime=extract_runtime(data),
            score="",
            series="FC2系列",
            directors=[],
            studio=studio,
            publisher=studio,
            thumb=cover_url,
            poster=cover_url,
            extrafanart=[],
            trailer="",
            image_download=False,
            mosaic="无码" if video_type == "無碼" else "有码",
            external_id=article_url,
            wanted="",
        )
        result = result_data.to_result()
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
