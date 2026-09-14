from pathlib import Path

from mdcx.core import avwiki, translate
from mdcx.core.avwiki import parse_avwiki_actor_search

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "avwiki"
SEARCH_FIXTURE = FIXTURE_DIR / "search_300MIUM-1431.html"
CONTEXT_FIXTURE = FIXTURE_DIR / "context_300MIUM-1431.html"


def test_avwiki_parser_handles_extra_and_reordered_classes():
    html = SEARCH_FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "300MIUM-1431")

    assert actor == "善場まみ"
    assert candidates
    assert candidates[0][0] == "300MIUM-1431"
    assert candidates[0][1] == actor


def test_avwiki_parser_preserves_suffix_number_matching():
    html = SEARCH_FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "MIUM-1431")

    assert actor == "善場まみ"
    assert candidates[0][0] == "300MIUM-1431"


def test_avwiki_parser_falls_back_to_number_and_actor_link_context():
    html = CONTEXT_FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "300MIUM-1431")

    assert actor == "善場まみ"
    assert candidates == [("300MIUM-1431", "善場まみ")]


def test_translate_uses_the_new_avwiki_lookup():
    assert translate.get_actorname is avwiki.get_actorname
