from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("MDCX_OFFLINE", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QFontMetrics, QRawFont
from PyQt6.QtWidgets import QApplication, QGroupBox, QLineEdit, QMainWindow, QScrollArea, QScrollBar, QWidget

import main
from mdcx.config.enums import DownloadableFile, FixedScrapingType
from mdcx.controllers.main_window import scrape_controller
from mdcx.controllers.main_window.init import setup_local_nfo_button, setup_result_sort_ui
from mdcx.controllers.main_window.nfo_controller import NFO_EDITOR_WIDGETS, NfoController
from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout, setup_responsive_ui
from mdcx.controllers.main_window.scrape_controller import ScrapeController
from mdcx.controllers.main_window.settings_page import SettingsPageController
from mdcx.controllers.main_window.site_priority_dialog import setup_site_priority_ui
from mdcx.controllers.main_window.style import _settings_semantic_style, apply_application_font
from mdcx.core import scraper as scraper_module
from mdcx.core.file import _get_folder_path
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo
from mdcx.signals import signal_qt
from mdcx.views.MDCx import Ui_MDCx
from tests.qt_font_support import CJK_VISUAL_SMOKE_TEXT, cjk_visual_test_font_error, configure_cjk_visual_test_font

APP = QApplication.instance() or QApplication([])


def _generated_window() -> QMainWindow:
    window = QMainWindow()
    window.Ui = Ui_MDCx()
    window.Ui.setupUi(window)
    window._sort_success_results = lambda: None
    window._toggle_result_sort_order = lambda: None
    window.main_load_nfo_click = lambda: None
    setup_result_sort_ui(window)
    setup_local_nfo_button(window)
    window.settings_controller = SettingsPageController(window)
    setup_responsive_ui(window)
    return window


def test_scrape_button_reaches_crawler_and_finishes_session(monkeypatch, tmp_path: Path):
    media_file = tmp_path / "ABC-123.mp4"
    media_file.write_bytes(b"test")
    crawler_calls: list[str] = []
    submitted = []

    class FakeCrawlerProvider:
        def __init__(self, *_args, **_kwargs):
            pass

        async def run(self, number: str) -> CrawlersResult:
            crawler_calls.append(number)
            result = CrawlersResult.empty()
            result.number = number
            result.title = "Integration result"
            return result

        async def close(self) -> None:
            pass

    async def fake_process_one_file(self, file_info: FileInfo, _file_mode: FileMode):
        result = await self.crawler_provider.run(file_info.number)
        return result, OtherInfo.empty()

    async def fake_get_file_info(_path: Path) -> FileInfo:
        info = FileInfo.empty()
        info.number = "ABC-123"
        info.short_number = "ABC-123"
        info.file_path = media_file
        info.file_name = media_file.name
        info.file_show_name = media_file.name
        info.file_show_path = media_file
        info.folder_path = media_file.parent
        info.file_ex = media_file.suffix
        return info

    async def no_op(*_args, **_kwargs):
        return None

    def fake_paths(*_args, **_kwargs):
        from mdcx.config.extend import MoviePathSetting

        return MoviePathSetting(
            movie_path=tmp_path,
            movie_paths=[tmp_path],
            success_folder=tmp_path,
            failed_folder=tmp_path,
            ignore_dirs=[],
            extrafanart_folder=tmp_path,
            softlink_path=tmp_path,
        )

    original_submit = scraper_module.executor.submit

    def capture_submit(coro, *, group=None):
        future = original_submit(coro, group=group)
        submitted.append(future)
        return future

    monkeypatch.setattr(scraper_module, "CrawlerProvider", FakeCrawlerProvider)
    monkeypatch.setattr(scraper_module.Scraper, "_process_one_file", fake_process_one_file)
    monkeypatch.setattr(scraper_module, "get_file_info_v2", fake_get_file_info)
    monkeypatch.setattr(scraper_module, "get_movie_path_setting", fake_paths)
    monkeypatch.setattr(scraper_module, "save_success_list", no_op)
    monkeypatch.setattr(scraper_module, "_clean_empty_fodlers", no_op)
    monkeypatch.setattr(scraper_module.executor, "submit", capture_submit)
    monkeypatch.setattr(scrape_controller, "get_remain_list", lambda: False)
    monkeypatch.setattr(scrape_controller, "start_new_scrape", scraper_module.start_new_scrape)
    monkeypatch.setattr(scraper_module.manager.config, "thread_number", 1)
    monkeypatch.setattr(scraper_module.manager.config, "thread_time", 0)
    monkeypatch.setattr(scraper_module.manager.config, "main_mode", 1)
    monkeypatch.setattr(scraper_module.manager.config, "switch_on", [])
    monkeypatch.setattr(scraper_module.manager.config, "scrape_softlink_path", False)
    monkeypatch.setattr(scraper_module.manager.config, "emby_on", [])
    monkeypatch.setattr(scraper_module.manager.config, "actor_photo_kodi_auto", False)

    window = _generated_window()
    controller = ScrapeController(window)
    window.Ui.pushButton_start_cap.setText("开始")
    controller.toggle()

    assert submitted, "UI/controller scrape entry did not submit a background task"
    submitted[-1].result(timeout=10)
    APP.processEvents()

    assert crawler_calls == ["ABC-123"]
    assert Flags.session is not None
    assert Flags.session.state.total_count == 1
    assert Flags.session.state.started_count == 1
    assert Flags.session.state.completed_count == 1
    assert Flags.session.state.success_count == 1
    assert Flags.session.state.failure_count == 0
    assert Flags.session.state.remain_queue == []
    assert Flags.failed_records == []
    window.close()
    signal_qt.stop = False
    Flags.reset()


@pytest.mark.asyncio
async def test_scrape_crawler_result_reaches_postprocess_without_copy_name_collision(monkeypatch, tmp_path: Path):
    media_file = tmp_path / "FC2-4933359.mp4"
    media_file.write_bytes(b"test")
    crawler_calls = []

    class PostprocessReached(Exception):
        pass

    class FakeFileScraper:
        def __init__(self, *_args, **_kwargs):
            pass

        async def run(self, task, _file_mode):
            crawler_calls.append(task.number)
            result = CrawlersResult.empty()
            result.number = task.number
            result.title = "FC2 title"
            result.actors = ["Actor"]
            return result

    async def true_check(*_args, **_kwargs):
        return True

    async def no_op_async(*_args, **_kwargs):
        return None

    async def stop_after_postprocess(*_args, **_kwargs):
        raise PostprocessReached

    def fake_paths(*_args, **_kwargs):
        from mdcx.config.extend import MoviePathSetting

        return MoviePathSetting(
            movie_path=tmp_path,
            movie_paths=[tmp_path],
            success_folder=tmp_path,
            failed_folder=tmp_path,
            ignore_dirs=[],
            extrafanart_folder=tmp_path,
            softlink_path=tmp_path,
        )

    info = FileInfo.empty()
    info.number = "FC2-4933359"
    info.short_number = info.number
    info.file_path = media_file
    info.file_name = media_file.name
    info.file_ex = media_file.suffix
    info.folder_path = tmp_path

    monkeypatch.setattr(scraper_module, "FileScraper", FakeFileScraper)
    monkeypatch.setattr(scraper_module, "check_file", true_check)
    monkeypatch.setattr(scraper_module, "get_movie_path_setting", fake_paths)
    monkeypatch.setattr(
        scraper_module,
        "classify_scrape_task",
        lambda *_args, **_kwargs: SimpleNamespace(scraping_type=FixedScrapingType.FC2),
    )
    monkeypatch.setattr(scraper_module, "show_result", lambda *_args: None)
    monkeypatch.setattr(scraper_module, "deal_some_field", lambda *_args: None)
    monkeypatch.setattr(scraper_module, "replace_special_word", lambda *_args: None)
    monkeypatch.setattr(scraper_module, "translate_title_outline", no_op_async)
    monkeypatch.setattr(scraper_module, "translate_actor", no_op_async)
    monkeypatch.setattr(scraper_module, "translate_info", lambda *_args: None)
    monkeypatch.setattr(scraper_module, "replace_word", lambda *_args: None)
    monkeypatch.setattr(scraper_module, "get_video_size", stop_after_postprocess)
    monkeypatch.setattr(scraper_module.manager.config, "main_mode", 1)
    monkeypatch.setattr(scraper_module.manager.config, "download_files", [DownloadableFile.NFO])
    Flags.reset()

    scraper = scraper_module.Scraper(crawler_provider=object())
    with pytest.raises(PostprocessReached):
        await scraper._process_one_file(info, FileMode.Default)

    assert crawler_calls == ["FC2-4933359"]
    Flags.reset()


def test_fc2_multilevel_folder_template_keeps_actor_segment(monkeypatch, tmp_path: Path):
    info = FileInfo.empty()
    info.file_path = tmp_path / "FC2-4933359.mp4"
    info.number = "FC2-4933359"
    info.definition = "4K"
    result = CrawlersResult.empty()
    result.number = info.number
    result.title = (
        "絶頂回数30回超え男性経験少ないメンエス嬢がハメ撮り体験で本能覚醒"
        "モニター越しに自分の痴態を見ながらガチイキする黒髪美女"
    )
    result.actors = ["佐野葉月"]

    monkeypatch.setattr(
        scraper_module.manager.config,
        "folder_name",
        "{{ actor }}/{{ number }} {{ title }} {{ actor }} {{ four_k }}",
    )
    monkeypatch.setattr(scraper_module.manager.config, "folder_name_max", 60)
    monkeypatch.setattr(scraper_module.manager.config, "success_file_move", True)
    monkeypatch.setattr(scraper_module.manager.config, "soft_link", 0)
    monkeypatch.setattr(scraper_module.manager.config, "main_mode", 1)

    _path, folder_name = _get_folder_path(tmp_path / "output", info, result)

    segments = folder_name.split("/")
    assert segments[0] == "佐野葉月"
    assert segments[1].startswith("FC2-4933359")
    assert "佐野葉月" in segments[1]
    assert segments[1].endswith("4K")
    assert all(len(segment) <= 60 for segment in segments)


def test_programmatic_name_preview_initialization_does_not_mark_settings_dirty():
    window = _generated_window()
    controller = window.settings_controller
    controller.mark_clean()

    window.Ui.plainTextEdit_name_template_preview.setPlainText("{{ number }}")

    assert controller._dirty_widgets == set()
    assert window.Ui.label_settings_dirty.text() == "已保存"
    window.close()


def test_qt_standard_context_menu_is_localized_to_chinese():
    assert main.install_qt_translations(APP)
    editor = QLineEdit("测试文本")
    editor.selectAll()
    menu = editor.createStandardContextMenu()
    action_texts = {action.text().replace("&", "") for action in menu.actions()}

    assert any("复制" in text for text in action_texts)
    assert any("全选" in text for text in action_texts)
    menu.deleteLater()
    editor.deleteLater()


def test_single_nfo_save_does_not_open_confirmation(monkeypatch):
    show_data = scraper_module.ShowData.empty()
    show_data.show_name = "one"
    show_data.data.title = "旧标题"
    label = SimpleNamespace(setText=lambda _text: None)
    window = SimpleNamespace(
        _nfo_batch_show_names=[],
        now_show_name="one",
        json_array={"one": show_data},
        Ui=SimpleNamespace(label_save_tips=label),
    )
    controller = NfoController(window)

    def read_field(field_name: str) -> str:
        if field_name == "title":
            return "新标题"
        return controller.data_field_value(show_data.data, field_name)

    saved = []
    monkeypatch.setattr(controller, "read_field", read_field)
    monkeypatch.setattr(controller, "confirm_changes", lambda *_args, **_kwargs: pytest.fail("unexpected dialog"))
    monkeypatch.setattr(controller, "save_entry", lambda *args: saved.append(args) or (True, [show_data]))

    assert set(NFO_EDITOR_WIDGETS).issuperset({"title"})
    assert controller.save() is True
    assert show_data.data.title == "新标题"
    assert len(saved) == 1


def _require_cjk_visual_test_font() -> str:
    family = configure_cjk_visual_test_font(APP)
    if family is None:
        pytest.skip(cjk_visual_test_font_error())
    return family


def test_cjk_font_available_for_settings_visual_layout():
    family = _require_cjk_visual_test_font()
    raw_font = QRawFont.fromFont(APP.font())

    assert APP.font().family() == family
    assert all(
        raw_font.supportsCharacter(ord(character))
        for character in CJK_VISUAL_SMOKE_TEXT
        if "\u4e00" <= character <= "\u9fff"
    )
    assert QFontMetrics(APP.font()).horizontalAdvance(CJK_VISUAL_SMOKE_TEXT) > 0


def test_settings_controls_use_the_resolved_application_font():
    family = _require_cjk_visual_test_font()

    assert apply_application_font() == family
    window = _generated_window()
    window.Ui.page_setting.setStyleSheet(_settings_semantic_style(False))
    settings_fonts = {
        widget.font().family() for widget in window.Ui.page_setting.findChildren(QWidget) if widget.objectName()
    }

    assert settings_fonts == {family}
    window.close()


def test_every_settings_page_remains_scrollable_at_supported_widths():
    _require_cjk_visual_test_font()
    window = _generated_window()
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.show()
    clipped_widgets: set[tuple[int, str, str, tuple[int, int, int, int], tuple[int, int, int, int]]] = set()

    for width in (880, 979, 980, 1100, 1239, 1240, 1440):
        window.resize(width, 760)
        apply_responsive_layout(window)
        APP.processEvents()
        for tab_index in range(window.Ui.tabWidget.count()):
            window.Ui.tabWidget.setCurrentIndex(tab_index)
            APP.processEvents()
            tab = window.Ui.tabWidget.currentWidget()
            scroll_areas = tab.findChildren(QScrollArea, options=Qt.FindChildOption.FindDirectChildrenOnly)
            assert len(scroll_areas) == 1
            scroll = scroll_areas[0]
            content = scroll.widget()
            assert content is not None
            assert content.width() <= scroll.viewport().width()

            visible_groups = [
                group
                for group in content.findChildren(
                    QGroupBox,
                    options=Qt.FindChildOption.FindDirectChildrenOnly,
                )
                if group.isVisible()
            ]
            assert visible_groups
            assert {group.x() for group in visible_groups} == {30}
            for group in visible_groups:
                assert group.height() > 0
                assert group.geometry().right() <= content.rect().right()
            if content is window.Ui.scrollAreaWidgetContents_xiazai:
                warning = window.Ui.label_310
                assert warning.x() <= 70
                assert warning.width() >= window.Ui.groupBox_24.width() - 100
                assert QFontMetrics(warning.font()).horizontalAdvance(warning.text()) <= warning.width()
                assert warning.y() > window.Ui.layoutWidget3.geometry().bottom()
            ordered_groups = sorted(visible_groups, key=lambda group: group.y())
            overlaps = [
                (
                    previous.objectName(),
                    previous.geometry().getRect(),
                    following.objectName(),
                    following.geometry().getRect(),
                )
                for previous, following in zip(ordered_groups, ordered_groups[1:], strict=False)
                if previous.geometry().bottom() >= following.geometry().top()
            ]
            assert not overlaps, (width, tab_index, overlaps)

            for child in content.findChildren(QWidget):
                if not child.isVisible() or isinstance(child, QScrollBar):
                    continue
                if not child.objectName().endswith("_validation_container"):
                    assert child.height() > 0, (width, tab_index, child.objectName())
                parent = child.parentWidget()
                if parent is None or isinstance(parent, QScrollArea):
                    continue
                if parent.objectName().endswith("_validation_container"):
                    continue
                if not parent.rect().adjusted(-2, -2, 2, 2).contains(child.geometry()):
                    clipped_widgets.add(
                        (
                            tab_index,
                            parent.objectName(),
                            child.objectName(),
                            parent.rect().getRect(),
                            child.geometry().getRect(),
                        )
                    )

            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
            APP.processEvents()
            last_group = max(visible_groups, key=lambda group: group.mapTo(content, QPoint()).y() + group.height())
            bottom = last_group.mapTo(scroll.viewport(), QPoint(0, last_group.height())).y()
            assert bottom <= scroll.viewport().height() + 2, (
                width,
                tab_index,
                last_group.objectName(),
                bottom,
                scroll.viewport().height(),
            )

    assert not clipped_widgets, sorted(clipped_widgets)
    assert not window.Ui.layoutWidget.isHidden(), "tool-page layout hid the website preference controls"
    assert not window.Ui.layoutWidget2.isHidden(), "website setup hid the download-page controls"
    window.close()


def test_page_scoped_layout_setup_does_not_hide_same_named_settings_widgets():
    window = _generated_window()
    tool_ui = next(
        page_ui
        for page_ui in window.Ui._page_views
        if getattr(page_ui, "scrollAreaWidgetContents_gongju", None) is window.Ui.scrollAreaWidgetContents_gongju
    )

    assert tool_ui.layoutWidget.isHidden()
    assert not window.Ui.layoutWidget.isHidden()
    assert not window.Ui.layoutWidget2.isHidden()

    setup_site_priority_ui(window)

    assert window.Ui.groupBox_35.isHidden()
    assert window.Ui.layoutWidget1.isHidden()
    assert not window.Ui.layoutWidget2.isHidden()
    window.close()
