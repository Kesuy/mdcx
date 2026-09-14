import re
from urllib.parse import quote

from lxml import etree

from ..config.manager import manager
from ..models.log_buffer import LogBuffer


def _normalize_avwiki_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _numbers_match(candidate: str, requested: str) -> bool:
    candidate_norm = _normalize_avwiki_number(candidate)
    requested_norm = _normalize_avwiki_number(requested)
    if not candidate_norm or not requested_norm:
        return False
    return (
        candidate_norm == requested_norm
        or candidate_norm.endswith(requested_norm)
        or requested_norm.endswith(candidate_norm)
    )


def _unique_texts(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _extract_actor_names(node) -> list[str]:
    actor_names = _unique_texts(
        node.xpath('.//li[contains(concat(" ", normalize-space(@class), " "), " actress-name ")]//a/text()')
    )
    if actor_names:
        return actor_names
    return _unique_texts(node.xpath('.//a[contains(@href, "/av-actress/")]//text()'))


def _node_contains_number(node, number: str) -> bool:
    requested = _normalize_avwiki_number(number)
    if not requested:
        return False
    text = " ".join(part.strip() for part in node.xpath(".//text()") if part and part.strip())
    return requested in _normalize_avwiki_number(text)


def _parse_contextual_candidates(root, number: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in root.xpath("//article | //header | //section"):
        if not _node_contains_number(node, number):
            continue
        actor_text = ",".join(_extract_actor_names(node))
        candidate = (number, actor_text)
        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def parse_avwiki_actor_search(html: str, number: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse AV-Wiki search/detail HTML and return the matched actor plus diagnostics."""
    if not str(html or "").strip():
        return "", []

    try:
        root = etree.fromstring(html, etree.HTMLParser(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid HTML: {exc}") from exc
    if root is None:
        return "", []

    result_nodes = root.xpath('//ul[contains(concat(" ", normalize-space(@class), " "), " post-meta ")]')
    candidates: list[tuple[str, str]] = []
    matched_actor = ""

    for node in result_nodes:
        actor_text = ",".join(_extract_actor_names(node))

        item_texts: list[str] = []
        for li in node.xpath("./li"):
            classes = str(li.get("class") or "").split()
            if "actress-name" in classes:
                continue
            text = " ".join(part.strip() for part in li.xpath(".//text()") if part and part.strip()).strip()
            if text:
                item_texts.append(text)

        matched_number = next((text for text in item_texts if _numbers_match(text, number)), "")
        display_number = matched_number or (item_texts[-1] if item_texts else "")
        candidates.append((display_number, actor_text))

        if not matched_actor and matched_number and actor_text:
            matched_actor = actor_text

    if matched_actor:
        return matched_actor, candidates

    contextual_candidates = _parse_contextual_candidates(root, number)
    for candidate in contextual_candidates:
        if candidate not in candidates:
            candidates.append(candidate)
        if not matched_actor and candidate[1]:
            matched_actor = candidate[1]

    return matched_actor, candidates


def _log_avwiki_candidates(number: str, candidates: list[tuple[str, str]], source: str) -> None:
    LogBuffer.log().write(f"\n 🔎 Av-wiki {source} results: {len(candidates)} for '{number}'")
    for candidate_number, actor_name in candidates:
        LogBuffer.log().write(
            f"\n 🔎 Av-wiki {source} candidate: number='{candidate_number or 'N/A'}' actor='{actor_name or 'N/A'}'"
        )


def _failure_reason(number: str, candidates: list[tuple[str, str]]) -> str:
    if not candidates:
        return "no matching result container found"
    if any(candidate_number and _numbers_match(candidate_number, number) for candidate_number, _ in candidates):
        return "matched number but actor name was empty"
    return "no result matched the requested number"


async def get_actorname(number: str) -> tuple[bool, str]:
    """Get the real Japanese actor name from AV-Wiki with a detail-page fallback."""
    search_url = f"https://av-wiki.net/?s={quote(number.strip())}"
    detail_slug = quote(number.strip().lower(), safe="-_.")
    detail_url = f"https://av-wiki.net/{detail_slug}/"
    failure_reasons: list[str] = []

    async with manager.acquire_computed() as computed:
        search_html, search_error = await computed.async_client.get_text(search_url)
        if search_html is None:
            failure_reasons.append(f"search request failed: {search_error}")
        else:
            LogBuffer.log().write(f"\n 🔎 Av-wiki search response: number='{number}' bytes={len(search_html)}")
            try:
                actor_name, candidates = parse_avwiki_actor_search(search_html, number)
            except ValueError as exc:
                failure_reasons.append(f"search parse failed: {exc}")
            else:
                _log_avwiki_candidates(number, candidates, "search")
                if actor_name:
                    return True, actor_name
                failure_reasons.append(f"search {_failure_reason(number, candidates)}")

        detail_html, detail_error = await computed.async_client.get_text(detail_url)
        if detail_html is None:
            failure_reasons.append(f"detail request failed: {detail_error}")
        else:
            LogBuffer.log().write(f"\n 🔎 Av-wiki detail response: number='{number}' bytes={len(detail_html)}")
            try:
                actor_name, candidates = parse_avwiki_actor_search(detail_html, number)
            except ValueError as exc:
                failure_reasons.append(f"detail parse failed: {exc}")
            else:
                _log_avwiki_candidates(number, candidates, "detail")
                if actor_name:
                    return True, actor_name
                failure_reasons.append(f"detail {_failure_reason(number, candidates)}")

    reason = "; ".join(failure_reasons) or "unknown AV-Wiki lookup failure"
    LogBuffer.log().write(f"\n 🔴 Av-wiki parse failed: number='{number}' reason='{reason}'")
    return False, reason
