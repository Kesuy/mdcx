import re
from urllib.parse import quote

from lxml import etree

from ..config.manager import manager
from ..models.log_buffer import LogBuffer


def _normalize_avwiki_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _avwiki_number_variants(value: str) -> list[str]:
    """Return lookup forms understood by AV-Wiki, keeping the original first.

    Some FANZA/MGS amateur numbers carry a three-digit distributor prefix in
    MDCx (for example 420HOI-304), while AV-Wiki indexes the maker number
    (HOI-304). We only strip that well-known three-digit form so unrelated
    numbers are not broadened accidentally.
    """
    original = str(value or "").strip().upper()
    if not original:
        return []

    variants = [original]
    match = re.fullmatch(r"\d{3}([A-Z][A-Z0-9]*-\d+)", original)
    if match:
        variants.append(match.group(1))
    return list(dict.fromkeys(variants))


def _normalized_number_variants(value: str) -> set[str]:
    return {_normalize_avwiki_number(item) for item in _avwiki_number_variants(value) if item}


def _numbers_match(candidate: str, requested: str) -> bool:
    candidate_variants = _normalized_number_variants(candidate)
    requested_variants = _normalized_number_variants(requested)
    return bool(candidate_variants and requested_variants and candidate_variants & requested_variants)


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
    requested_variants = _normalized_number_variants(number)
    if not requested_variants:
        return False
    text = " ".join(part.strip() for part in node.xpath(".//text()") if part and part.strip())
    normalized_text = _normalize_avwiki_number(text)
    return any(variant in normalized_text for variant in requested_variants)


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


async def _try_avwiki_page(client, *, requested_number: str, lookup_number: str, url: str, source: str):
    page_html, page_error = await client.get_text(url)
    if page_html is None:
        return "", f"{source} request failed: {page_error}"

    LogBuffer.log().write(
        f"\n 🔎 Av-wiki {source} response: number='{requested_number}' lookup='{lookup_number}' bytes={len(page_html)}"
    )
    try:
        actor_name, candidates = parse_avwiki_actor_search(page_html, requested_number)
    except ValueError as exc:
        return "", f"{source} parse failed: {exc}"

    _log_avwiki_candidates(requested_number, candidates, f"{source}[{lookup_number}]")
    if actor_name:
        return actor_name, ""
    return "", f"{source} {_failure_reason(requested_number, candidates)}"


async def get_actorname(number: str) -> tuple[bool, str]:
    """Get the real Japanese actor name from AV-Wiki with prefixed-number fallbacks."""
    lookup_numbers = _avwiki_number_variants(number)
    if not lookup_numbers:
        return False, "empty AV-Wiki lookup number"

    failure_reasons: list[str] = []
    async with manager.acquire_computed() as computed:
        for lookup_number in lookup_numbers:
            search_url = f"https://av-wiki.net/?s={quote(lookup_number)}"
            actor_name, failure = await _try_avwiki_page(
                computed.async_client,
                requested_number=number,
                lookup_number=lookup_number,
                url=search_url,
                source="search",
            )
            if actor_name:
                if lookup_number != number.strip().upper():
                    LogBuffer.log().write(
                        f"\n 🟢 Av-wiki matched prefixed number '{number}' via maker number '{lookup_number}'"
                    )
                return True, actor_name
            failure_reasons.append(f"{lookup_number}: {failure}")

        # Search first with every safe alias. Only then try direct detail pages,
        # prioritising the maker-number form because AV-Wiki article slugs use it.
        for lookup_number in reversed(lookup_numbers):
            detail_slug = quote(lookup_number.lower(), safe="-_.")
            detail_url = f"https://av-wiki.net/{detail_slug}/"
            actor_name, failure = await _try_avwiki_page(
                computed.async_client,
                requested_number=number,
                lookup_number=lookup_number,
                url=detail_url,
                source="detail",
            )
            if actor_name:
                if lookup_number != number.strip().upper():
                    LogBuffer.log().write(
                        f"\n 🟢 Av-wiki matched prefixed number '{number}' via maker number '{lookup_number}'"
                    )
                return True, actor_name
            failure_reasons.append(f"{lookup_number}: {failure}")

    reason = "; ".join(failure_reasons) or "unknown AV-Wiki lookup failure"
    LogBuffer.log().write(f"\n 🔴 Av-wiki parse failed: number='{number}' reason='{reason}'")
    return False, reason
