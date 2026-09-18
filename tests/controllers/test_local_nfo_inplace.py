from pathlib import Path

from mdcx.controllers.main_window.local_nfo_inplace import LocalNfoInplaceMixin
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo, ShowData


def _show_data(file_path: Path, *, number: str, local: bool = True) -> ShowData:
    file_info = FileInfo.empty()
    file_info.file_path = file_path
    file_info.file_name = file_path.stem
    file_info.file_ex = file_path.suffix
    file_info.number = number
    data = CrawlersResult.empty()
    data.number = number
    return ShowData(
        file_info=file_info,
        data=data,
        other=OtherInfo.empty(),
        show_name=("本地." if local else "1.") + file_path.stem,
    )


class _Harness(LocalNfoInplaceMixin):
    def __init__(self, show_data: ShowData | None):
        self.show_data = show_data
        self.selected = (
            None if show_data is None else (None, show_data.show_name, show_data, show_data.file_info.file_path)
        )

    def _get_single_selected_entry(self):
        return self.selected


def test_local_nfo_rescrape_prefills_canonical_nfo_number_not_filename_stem():
    file_path = Path("FZ88 御藤静.mp4")
    harness = _Harness(_show_data(file_path, number="FZ88"))

    assert harness._local_nfo_default_number(file_path, file_path.name) == "FZ88"


def test_non_local_rescrape_keeps_filename_stem_fallback():
    file_path = Path("FZ88 御藤静.mp4")
    harness = _Harness(_show_data(file_path, number="FZ88", local=False))

    assert harness._local_nfo_default_number(file_path, file_path.name) == "FZ88 御藤静"
