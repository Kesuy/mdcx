from pathlib import Path

from mdcx.core.avwiki import parse_avwiki_actor_search

FIXTURE = Path(__file__).parent / "fixtures" / "avwiki" / "search_300MIUM-1431.html"


def test_avwiki_parser_handles_extra_and_reordered_classes():
    html = FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "300MIUM-1431")

    assert actor
    assert candidates
    assert candidates[0][0] == "300MIUM-1431"
    assert candidates[0][1] == actor


def test_avwiki_parser_preserves_suffix_number_matching():
    html = FIXTURE.read_text(encoding="utf-8")

    actor, candidates = parse_avwiki_actor_search(html, "MIUM-1431")

    assert actor
    assert candidates[0][0] == "300MIUM-1431"
