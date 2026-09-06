from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MDCX_OFFLINE", "1")

from PIL import Image
from PyQt6.QtWidgets import QApplication, QDialog

from mdcx.config.enums import FixedScrapingType, Website
from mdcx.controllers.cut_window import CutWindow
from mdcx.controllers.main_window.site_priority_dialog import FieldPriorityDialog, SiteListEditorDialog
from ui_runtime_audit import _configure_cjk_font, _render_widget


def _parent(dark: bool = False) -> QDialog:
    parent = QDialog()
    parent.dark_mode = dark
    parent.options = None
    return parent


def _show_and_capture(widget, path: Path) -> None:
    widget.show()
    QApplication.processEvents()
    _render_widget(widget, path, quality=82)
    widget.hide()
    widget.deleteLater()
    QApplication.processEvents()


def main() -> None:
    output = Path("ui-audit/windows-dialogs")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _configure_cjk_font(app)

    sites = [Website.JAVDB, Website.JAVBUS, Website.DMM, Website.MGSTAGE]

    parent = _parent(False)
    site_dialog = SiteListEditorDialog("编辑网站源", [Website.JAVDB, Website.JAVBUS], sites, parent)
    _show_and_capture(site_dialog, output / "site-list-editor-light.jpg")
    parent.close()

    parent = _parent(True)
    priority_dialog = FieldPriorityDialog(
        "字段优先级",
        FixedScrapingType.YOUMA,
        sites,
        {},
        parent,
    )
    _show_and_capture(priority_dialog, output / "field-priority-dark.jpg")
    parent.close()

    parent = _parent(False)
    cut_window = CutWindow(parent)
    image_path = output / "sample-fanart.jpg"
    Image.new("RGB", (1280, 720), "navy").save(image_path)
    image_data = SimpleNamespace(
        number="TEST-001",
        has_sub=False,
        mosaic="有码",
        definition="1080p",
        file_path=Path(r"D:\Media\TEST-001.mp4"),
    )
    cut_window.showimage(image_path, image_data)
    _show_and_capture(cut_window, output / "cut-window.jpg")
    parent.close()


if __name__ == "__main__":
    main()
