from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.types import CrawlersResult, FieldProvenance


def test_field_provenance_tracks_value_source_translation_and_priority_chain():
    result = CrawlersResult.empty()
    result.record_provenance(
        CrawlerResultFields.TITLE,
        "原始标题",
        "javdb",
        priority_chain=("javdb", "dmm"),
    )
    result.mark_provenance_translated(CrawlerResultFields.TITLE, "翻译标题")

    provenance = result.get_provenance(CrawlerResultFields.TITLE)

    assert provenance == FieldProvenance("翻译标题", "javdb", True, ("javdb", "dmm"))
    assert "已翻译" in provenance.describe()


def test_major_metadata_fields_accept_independent_provenance_without_changing_values():
    result = CrawlersResult.empty()
    fields = (
        CrawlerResultFields.TITLE,
        CrawlerResultFields.ORIGINALTITLE,
        CrawlerResultFields.ACTORS,
        CrawlerResultFields.STUDIO,
        CrawlerResultFields.DIRECTORS,
        CrawlerResultFields.TAGS,
        CrawlerResultFields.OUTLINE,
        CrawlerResultFields.POSTER,
        "fanart",
    )
    for field in fields:
        result.record_provenance(field, f"value-{field}", "dmm")

    assert all(result.get_provenance(field).source == "dmm" for field in fields)  # type: ignore[union-attr]


def test_image_fallback_updates_final_value_and_source_without_touching_metadata_value():
    result = CrawlersResult.empty()
    result.poster = "https://javdb.example/poster.jpg"
    result.record_provenance(CrawlerResultFields.POSTER, result.poster, "javdb", priority_chain=("javdb", "dmm"))

    result.poster = "https://amazon.example/poster.jpg"
    result.poster_from = "Amazon"

    provenance = result.get_provenance(CrawlerResultFields.POSTER)
    assert result.poster == "https://amazon.example/poster.jpg"
    assert provenance is not None
    assert provenance.value == result.poster
    assert provenance.source == "Amazon"
    assert provenance.priority_chain == ("Amazon", "javdb", "dmm")
