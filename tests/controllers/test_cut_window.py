# ruff: noqa: E402, I001

import asyncio
import os
import stat
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog

from mdcx.config.enums import DownloadableFile
from mdcx.config.manager import manager
from mdcx.controllers.cut_window import CutWindow


APP = QApplication.instance() or QApplication([])


def _window() -> CutWindow:
    parent = QDialog()
    parent.dark_mode = False
    parent.options = None
    window = CutWindow(parent)
    window._test_parent = parent
    return window


def _image_data(file_path=None):
    return SimpleNamespace(
        number="TEST-001",
        has_sub=False,
        mosaic="有码",
        definition="",
        file_path=file_path,
    )


def test_open_image_defaults_to_current_movie_directory(tmp_path, monkeypatch):
    movie_directory = tmp_path / "movies" / "TEST-001"
    movie_directory.mkdir(parents=True)
    movie_path = movie_directory / "TEST-001.mp4"
    movie_path.touch()
    image_directory = tmp_path / "artwork"
    image_directory.mkdir()
    image_path = image_directory / "TEST-001-fanart.jpg"
    Image.new("RGB", (120, 80), "navy").save(image_path)
    selected = {}

    def fake_open_file_name(parent, title, directory, file_filter, *, options):
        selected.update(
            parent=parent,
            title=title,
            directory=directory,
            file_filter=file_filter,
            options=options,
        )
        return "", ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_open_file_name)
    window = _window()
    try:
        window.showimage(image_path, _image_data(movie_path))
        window.open_image()

        assert selected["parent"] is window
        assert selected["directory"] == movie_directory.as_posix()
        assert "*.webp" in selected["file_filter"]
    finally:
        window.close()


def test_crop_ratio_controls_offer_requested_presets():
    window = _window()
    try:
        choices = [
            window.Ui.comboBox_cut_ratio.itemText(index) for index in range(window.Ui.comboBox_cut_ratio.count())
        ]
        assert choices == ["默认", "原比例", "2:3", "3:2", "16:9", "9:16"]
        assert window.Ui.checkBox_keep_ratio.text() == "保持比例"
        assert window.Ui.checkBox_keep_ratio.isChecked() is True
        assert window.Ui.pushButton_rotate_left.text() == "↶ 左旋 90°"
        assert window.Ui.pushButton_rotate_right.text() == "↷ 右旋 90°"
    finally:
        window.close()


def test_locked_two_to_three_ratio_keeps_height_and_width_synchronized():
    window = _window()
    try:
        window.pic_new_w = 800
        window.pic_new_h = 600
        window.Ui.comboBox_cut_ratio.setCurrentText("2:3")
        window.Ui.checkBox_keep_ratio.setChecked(True)

        window.Ui.horizontalSlider_right.setValue(2500)

        rect = window.pushButton_select_cutrange.geometry()
        assert rect.width() == 200
        assert rect.height() == 300
        assert window.Ui.label_cut_ratio.text() == "1.50"
        assert window.Ui.horizontalSlider_left.value() == 5000
    finally:
        window.close()


def test_unlocked_crop_sliders_can_change_only_one_dimension():
    window = _window()
    try:
        window.pic_new_w = 800
        window.pic_new_h = 600
        window._apply_crop_rect(window.pushButton_select_cutrange.geometry(), sync_sliders=True)
        initial_height = window.pushButton_select_cutrange.height()
        window.Ui.checkBox_keep_ratio.setChecked(False)

        window.Ui.horizontalSlider_right.setValue(3000)

        assert window.pushButton_select_cutrange.width() == 240
        assert window.pushButton_select_cutrange.height() == initial_height
    finally:
        window.close()


def test_repeated_rotation_updates_preview_dimensions_and_crop_source(tmp_path):
    image_path = tmp_path / "TEST-001-fanart.jpg"
    Image.new("RGB", (1200, 800), "navy").save(image_path)
    window = _window()
    try:
        window.showimage(image_path, _image_data())
        assert (window.pic_w, window.pic_h) == (1200, 800)

        window.rotate_right()
        assert (window.pic_w, window.pic_h) == (800, 1200)
        assert window.rotation_quarters == 1

        window.rotate_right()
        assert (window.pic_w, window.pic_h) == (1200, 800)
        assert window.rotation_quarters == 2

        window.rotate_left()
        assert (window.pic_w, window.pic_h) == (800, 1200)
        assert window.rotation_quarters == 1

        with Image.open(image_path) as source:
            rotated = window._rotate_pil_image(source)
            assert rotated.size == (800, 1200)
    finally:
        window.close()


@pytest.mark.parametrize(
    ("quarters", "expected_size", "expected_pixels"),
    [
        (0, (2, 3), [1, 2, 3, 4, 5, 6]),
        (1, (3, 2), [5, 3, 1, 6, 4, 2]),
        (2, (2, 3), [6, 5, 4, 3, 2, 1]),
        (3, (3, 2), [2, 4, 6, 1, 3, 5]),
    ],
)
def test_pillow_quarter_turns_preserve_clockwise_pixel_orientation(quarters, expected_size, expected_pixels):
    window = _window()
    source = Image.new("L", (2, 3))
    source.putdata([1, 2, 3, 4, 5, 6])
    try:
        window.rotation_quarters = quarters
        rotated = window._rotate_pil_image(source)

        assert rotated.size == expected_size
        assert list(rotated.getdata()) == expected_pixels
    finally:
        source.close()
        window.close()


def test_same_path_rotation_save_failure_preserves_source_and_cleans_temporary_file(tmp_path):
    class FailingImage:
        @staticmethod
        def save(file_object, **_kwargs):
            file_object.write(b"partial")
            raise OSError("simulated save failure")

    source_path = tmp_path / "TEST-001-fanart.jpg"
    source_path.write_bytes(b"original")
    window = _window()
    try:
        with pytest.raises(OSError, match="simulated save failure"):
            window._save_full_image(FailingImage(), source_path, source_path)

        assert source_path.read_bytes() == b"original"
        assert not list(tmp_path.glob(".*.mdcx-rotate-*"))
    finally:
        window.close()


@pytest.mark.parametrize("fchmod_available", [True, False])
def test_same_path_rotation_preserves_source_permissions(tmp_path, monkeypatch, fchmod_available):
    if not fchmod_available:
        monkeypatch.delattr(os, "fchmod")
    source_path = tmp_path / "TEST-001-fanart.jpg"
    Image.new("RGB", (12, 8), "navy").save(source_path)
    source_path.chmod(0o600)
    window = _window()
    rotated = Image.new("RGB", (8, 12), "navy")
    try:
        window._save_full_image(rotated, source_path, source_path)

        assert stat.S_IMODE(source_path.stat().st_mode) == 0o600
    finally:
        rotated.close()
        window.close()


@pytest.mark.parametrize(
    ("source_name", "other_output_attr"),
    [("TEST-001-fanart.jpg", "cut_thumb_path"), ("TEST-001-thumb.jpg", "cut_fanart_path")],
)
def test_rotated_art_source_is_overwritten_with_same_orientation_as_other_outputs(
    tmp_path, monkeypatch, source_name, other_output_attr
):
    class Parent(QDialog):
        def __init__(self):
            super().__init__()
            self.dark_mode = False
            self.options = None
            self.change_to_mainpage = SimpleNamespace(emit=lambda _value: None)
            self.img_path = None

        def show_log_text(self, _text):
            pass

        async def _set_pixmap(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.THUMB, DownloadableFile.FANART])
    monkeypatch.setattr(manager.config, "poster_mark", False)
    monkeypatch.setattr(manager.config, "thumb_mark", False)
    monkeypatch.setattr(manager.config, "fanart_mark", False)
    monkeypatch.setattr(manager.config, "pic_simple_name", False)

    image_path = tmp_path / source_name
    Image.new("RGB", (120, 80), "navy").save(image_path)
    parent = Parent()
    window = CutWindow(parent)
    try:
        window.showimage(image_path, _image_data())
        window.rotate_right()

        assert asyncio.run(window.to_cut()) is True

        with Image.open(image_path) as source:
            assert source.size == (80, 120)
        with Image.open(getattr(window, other_output_attr)) as other_output:
            assert other_output.size == (80, 120)
    finally:
        window.close()
        parent.close()
