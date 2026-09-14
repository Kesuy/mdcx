import re

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


def parse_avwiki_actor_search(html: str, number: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse AV-Wiki search results and return the matched actor plus diagnostics."""
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
        actor_names = [
            text.strip()
            for text in node.xpath(
                './/li[contains(concat(" ", normalize-space(@class), " "), " actress-name ")]//a/text()'
            )
            if text and text.strip()
        ]
        actor_text = ",".join(dict.fromkeys(actor_names))

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

    return matched_actor, candidates


def _log_avwiki_candidates(number: str, candidates: list[tuple[str, str]]) -> None:
    LogBuffer.log().write(f"\n 🔎 Av-wiki results: {len(candidates)} for '{number}'")
    for candidate_number, actor_name in candidates:
        LogBuffer.log().write(
            f"\n 🔎 Av-wiki candidate: number='{candidate_number or 'N/A'}' actor='{actor_name or 'N/A'}'"
        )


async def get_actorname(number: str) -> tuple[bool, str]:
    """Get the real Japanese actor name from AV-Wiki with parse diagnostics."""
    url = f"https://av-wiki.net/?s={number}"
    async with manager.acquire_computed() as computed:
        html, error = await computed.async_client.get_text(url)

    if html is None:
        reason = f"request failed: {error}"
        LogBuffer.log().write(f"\n 🔴 Av-wiki parse failed: number='{number}' reason='{reason}'")
        return False, reason

    try:
        actor_name, candidates = parse_avwiki_actor_search(html, number)
    except ValueError as exc:
        reason = str(exc)
        LogBuffer.log().write(f"\n 🔴 Av-wiki parse failed: number='{number}' reason='{reason}'")
        return False, reason

    _log_avwiki_candidates(number, candidates)
    if actor_name:
        return True, actor_name

    if not candidates:
        reason = "no post-meta search results found"
    elif any(candidate_number and _numbers_match(candidate_number, number) for candidate_number, _ in candidates):
        reason = "matched number but actor name was empty"
    else:
        reason = "no result matched the requested number"

    LogBuffer.log().write(f"\n 🔴 Av-wiki parse failed: number='{number}' reason='{reason}'")
    return False, reason
