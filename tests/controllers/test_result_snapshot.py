from mdcx.controllers.main_window.main_page_mixin import MainPageMixin
from mdcx.controllers.main_window.result_snapshot import load_result_snapshot, save_result_snapshot
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.failure import FailureCategory, FailureRecord
from mdcx.models.flags import Flags
from mdcx.models.types import FieldProvenance, ShowData


def test_result_snapshot_round_trips_display_data(tmp_path):
    show_data = ShowData.empty()
    show_data.show_name = "1-1.FC2-1234567"
    show_data.file_info.number = "FC2-1234567"
    show_data.file_info.file_path = tmp_path / "FC2-1234567.mp4"
    show_data.file_info.file_show_path = show_data.file_info.file_path
    show_data.file_info.folder_path = tmp_path
    show_data.file_info.file_name = "FC2-1234567"
    show_data.file_info.file_ex = ".mp4"
    show_data.data.number = "FC2-1234567"
    show_data.data.title = "测试标题"
    show_data.data.actors = ["演员A", "演员B"]
    show_data.data.field_sources[CrawlerResultFields.TITLE] = "fc2ppvdb"
    show_data.data.provenance[CrawlerResultFields.TITLE.value] = FieldProvenance(
        value="测试标题",
        source="fc2ppvdb",
        priority_chain=("fc2ppvdb", "fc2"),
    )
    show_data.other.poster_path = tmp_path / "poster.jpg"
    snapshot = tmp_path / "results.json"

    save_result_snapshot(snapshot, [("succ", show_data)])
    records = load_result_snapshot(snapshot)

    assert len(records) == 1
    status, restored = records[0]
    assert status == "succ"
    assert restored.show_name == show_data.show_name
    assert restored.file_info.file_path == show_data.file_info.file_path
    assert restored.data.title == "测试标题"
    assert restored.data.actors == ["演员A", "演员B"]
    assert restored.data.field_sources[CrawlerResultFields.TITLE] == "fc2ppvdb"
    assert restored.data.get_provenance(CrawlerResultFields.TITLE).source == "fc2ppvdb"
    assert restored.other.poster_path == tmp_path / "poster.jpg"


def test_failed_result_path_follows_failure_record_after_file_move(tmp_path):
    actual_path = tmp_path / "failed" / "FC2-1254113.mp4"
    actual_path.parent.mkdir()
    actual_path.write_bytes(b"video")

    show_data = ShowData.empty()
    show_data.show_name = "1-1.FC2-1254113"
    show_data.file_info.file_path = tmp_path / "source" / "FC2-1254113.mp4"
    record = FailureRecord(
        actual_path,
        "scrape",
        FailureCategory.SEARCH_NO_RESULT,
        "未获取",
        False,
        context={"show_name": show_data.show_name, "number": "FC2-1254113"},
    )
    previous_records = Flags.failed_records
    Flags.failed_records = [record]
    try:
        resolved = MainPageMixin._resolve_result_file_path(object(), show_data)
    finally:
        Flags.failed_records = previous_records

    assert resolved == actual_path
    assert show_data.file_info.file_path == actual_path
    assert show_data.file_info.folder_path == actual_path.parent
    assert show_data.file_info.file_name == "FC2-1254113"
    assert show_data.file_info.file_ex == ".mp4"
